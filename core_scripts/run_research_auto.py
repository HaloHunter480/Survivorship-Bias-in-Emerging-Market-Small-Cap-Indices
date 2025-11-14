#!/usr/bin/env python3
"""
Automatic Research Runner – No user input required
"""

import sys
from pathlib import Path

# Import the main research class
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

from run_complete_research import CompleteSurvivorshipResearch


# Configuration
BHAVCOPIES_DIR = Path("data/raw")   


print("\n🚀 STARTING SURVIVORSHIP BIAS RESEARCH")
print(f"Processing bhavcopies from: {BHAVCOPIES_DIR}")
print("=" * 80)
print()

# Run automatically
research = CompleteSurvivorshipResearch(BHAVCOPIES_DIR)
research.run_complete_pipeline()

print("\n✅ DONE! Check the results/ folder for outputs.")
