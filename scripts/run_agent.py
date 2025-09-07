
import argparse
import os
import sys

# Ensure the project root (parent of this file) is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent.job_agent import run


def main():
    parser = argparse.ArgumentParser(description='Run the Enhanced Job AI Agent')
    parser.add_argument('--config', type=str, default='config/config.yaml', help='Path to YAML config file')
    args = parser.parse_args()
    rp = run(args.config)
    print(rp)


if __name__ == '__main__':
    main()
