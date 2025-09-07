
import argparse
from .job_agent import run

def main():
    parser = argparse.ArgumentParser(description='Run the Enhanced Job AI Agent')
    parser.add_argument('--config', type=str, default='config/config.yaml', help='Path to YAML config file')
    args = parser.parse_args()
    rp = run(args.config)
    print(rp)

if __name__ == '__main__':
    main()
