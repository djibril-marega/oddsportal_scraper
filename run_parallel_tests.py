import json
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
import ctypes 

ctypes.windll.kernel32.SetThreadExecutionState(0x00000001 |0x00000002)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run tests in parallel')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Display test output in real time')
    return parser.parse_args()

def ensure_logs_dir():
    """Create logs directory if it doesn't exist"""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    return logs_dir

def generate_log_filename(config, timestamp):
    """Generate a log filename based on configuration and timestamp"""
    # Create a filesystem-safe name
    safe_sport = "".join(c for c in config['sport'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_region = "".join(c for c in config['region'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    try:
        safe_competition = "".join(c for c in config['competition'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{timestamp}_{safe_sport}_{safe_region}_{safe_competition}.log"
    except KeyError:
        safe_team = "".join(c for c in config['team'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{timestamp}_{safe_sport}_{safe_region}_{safe_team}.log"
    # Replace spaces with underscores and limit length
    filename = filename.replace(' ', '_')[:100]
    return filename

async def run_test(config, verbose=False, logs_dir=None):
    """Execute a test with a specific configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = generate_log_filename(config, timestamp)
    log_filepath = logs_dir / log_filename

    # Extract parameters
    competition = config.get("competition")
    team = config.get("team")
    teamid = config.get("teamid")
    typegame = config.get("typegame")

    # check mutual exclusivity
    if not competition and not (team and teamid):
        raise ValueError("Il faut soit 'competition', soit ('team' et 'teamid').")

    if competition and (team or teamid):
        raise ValueError("Vous ne pouvez pas définir 'competition' en même temps que 'team' ou 'teamid'.")

    # base command
    cmd = [
        sys.executable, "-m", "pytest",
        "test_oddsportal.py",
        f"--sport={config['sport']}",
        f"--region={config['region']}",
        f"--season={config['season']}",
        f"--bookmaker={config['bookmaker']}"
    ]

    # add either competition or team parameters
    if competition:
        cmd.append(f"--competition={competition}")
    else:
        cmd.append(f"--team={team}")
        cmd.append(f"--teamid={teamid}")
    if "spread" in config and config["spread"] is not None:
        cmd.append(f"--spread={config['spread']}")
    if typegame:
        cmd.append(f"--typegame={typegame}")

    # general pytest options
    cmd += ["-v", "--tb=short"]

    # JUnit XML logging
    if logs_dir:
        cmd += [f"--junitxml={log_filepath}"]


    
    if verbose:
        cmd.append("-s")  # Add -s option for pytest in verbose mode
    
    print(f"Starting test with configuration: {config}")
    
    if verbose:
        print(f"Command executed: {' '.join(cmd)}")
        print(f"Log file: {log_filepath}")
    
    try:
        # Open log file for writing
        with open(log_filepath, 'w', encoding='utf-8') as log_file:
            log_file.write(f"Test execution started at: {datetime.now().isoformat()}\n")
            log_file.write(f"Configuration: {config}\n")
            log_file.write(f"Command: {' '.join(cmd)}\n")
            log_file.write("-" * 80 + "\n\n")
            
            # Create process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout_text = ""
            stderr_text = ""
            
            if verbose:
                # Verbose mode: display output in real time and write to file
                async def read_stream(stream, stream_name):
                    nonlocal stdout_text, stderr_text
                    while True:
                        chunk = await stream.read(4096)  # lit 4 Ko à la fois
                        if not chunk:
                            break
                        try:
                            decoded = chunk.decode('utf-8', errors='replace')
                        except UnicodeDecodeError:
                            decoded = chunk.decode('latin-1', errors='replace')

                        # Affiche et écrit en temps réel
                        if decoded.strip():
                            print(f"[{stream_name}] {decoded}", end="")
                            log_file.write(f"[{stream_name}] {decoded}")
                            log_file.flush()

                        # Stocke pour retour final
                        if stream_name == "stdout":
                            stdout_text += decoded
                        else:
                            stderr_text += decoded

                
                # Read stdout and stderr in parallel
                await asyncio.gather(
                    read_stream(process.stdout, "stdout"),
                    read_stream(process.stderr, "stderr")
                )
            else:
                # Silent mode: wait without displaying, but write to file
                stdout, stderr = await process.communicate()
                
                # Decode outputs
                try:
                    stdout_text = stdout.decode('utf-8') if stdout else ""
                except UnicodeDecodeError:
                    stdout_text = stdout.decode('latin-1', errors='replace') if stdout else ""
                
                try:
                    stderr_text = stderr.decode('utf-8') if stderr else ""
                except UnicodeDecodeError:
                    stderr_text = stderr.decode('latin-1', errors='replace') if stderr else ""
                
                # Write to log file
                log_file.write("STDOUT:\n")
                log_file.write(stdout_text)
                log_file.write("\n\nSTDERR:\n")
                log_file.write(stderr_text)
            
            # Wait for process to finish
            returncode = await process.wait()
            
            # Write return code to log file
            log_file.write(f"\n\nProcess finished with return code: {returncode}\n")
            log_file.write(f"Test execution finished at: {datetime.now().isoformat()}\n")
        
        return {
            "config": config,
            "returncode": returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "log_file": str(log_filepath)
        }
    except Exception as e:
        error_msg = f"Error while executing test {config}: {e}"
        print(error_msg)
        
        # Write error to log file
        with open(log_filepath, 'a', encoding='utf-8') as log_file:
            log_file.write(f"\n\nERROR: {error_msg}\n")
            import traceback
            traceback.print_exc(file=log_file)
        
        return {
            "config": config,
            "returncode": -1,
            "stdout": "",
            "stderr": error_msg,
            "log_file": str(log_filepath)
        }

async def main(verbose=False):
    # Create logs directory
    logs_dir = ensure_logs_dir()
    
    # Load configurations
    try:
        with open("test_configs.json", "r", encoding='utf-8') as f:
            configs = json.load(f)
    except FileNotFoundError:
        print("Error: test_configs.json file does not exist")
        return
    except json.JSONDecodeError:
        print("Error: test_configs.json is not a valid JSON file")
        return
    
    # Limit number of concurrent tests
    semaphore = asyncio.Semaphore(3)
    
    async def run_with_semaphore(config):
        async with semaphore:
            return await run_test(config, verbose, logs_dir)
    
    # Run all tests in parallel
    tasks = [run_with_semaphore(config) for config in configs]
    logs = await asyncio.gather(*tasks)
    
    # Display logs
    print("\n" + "="*60)
    print("TEST logs")
    print("="*60)
    
    all_passed = True
    for result in logs:
        try:
            config_str = f"{result['config']['sport']} - {result['config']['region']} - {result['config']['competition']}"
        except KeyError:
            config_str = f"{result['config']['sport']} - {result['config']['region']} - {result['config']['team']}"
        
        if result['returncode'] == 0:
            print(f"✓ {config_str}: SUCCESS")
            print(f"   Log: {result.get('log_file', 'N/A')}")
        else:
            print(f"✗ {config_str}: FAILED")
            print(f"   Log: {result.get('log_file', 'N/A')}")
            
            # Display error safely
            error_msg = "Unknown error"
            if result['stderr']:
                error_lines = result['stderr'].splitlines()
                if error_lines:
                    error_msg = error_lines[-1]
            elif result['stdout']:
                error_lines = result['stdout'].splitlines()
                if error_lines:
                    error_msg = error_lines[-1]
                    
            print(f"   Error: {error_msg}")
            all_passed = False
    
    # Create a summary report
    summary_file = logs_dir / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("TEST EXECUTION SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Execution time: {datetime.now().isoformat()}\n")
        f.write(f"Total tests: {len(logs)}\n")
        f.write(f"Passed: {sum(1 for r in logs if r['returncode'] == 0)}\n")
        f.write(f"Failed: {sum(1 for r in logs if r['returncode'] != 0)}\n\n")
        
        for result in logs:
            status = "PASS" if result['returncode'] == 0 else "FAIL"
            try:
                f.write(f"{status}: {result['config']['sport']} - {result['config']['region']} - {result['config']['competition']}\n")
            except KeyError:
                f.write(f"{status}: {result['config']['sport']} - {result['config']['region']} - {result['config']['team']}\n")

            f.write(f"  Log file: {result.get('log_file', 'N/A')}\n")
            if result['returncode'] != 0:
                error_msg = result['stderr'] or result['stdout'] or "Unknown error"
                f.write(f"  Error: {error_msg[:200]}...\n")
            f.write("\n")
    
    print("="*60)
    print(f"Detailed report: {summary_file}")
    if all_passed:
        print("All tests passed successfully!")
    else:
        print("Some tests failed.")
    print("="*60)
    
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    args = parse_arguments()
    asyncio.run(main(verbose=args.verbose))
    ctypes.windll.kernel32.SetThreadExecutionState(0x00000001)