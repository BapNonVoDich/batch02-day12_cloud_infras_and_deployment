import os
import sys
from dotenv import load_dotenv

# Add src and tools to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from tools.menu_recommendation import recommend_daily_menu

def main():
    load_dotenv()
    print("Testing recommend_daily_menu...")
    try:
        res = recommend_daily_menu("user_1")
        print("\n--- Result ---")
        print(res)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
