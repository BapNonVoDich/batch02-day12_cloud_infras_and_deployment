import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent

def test_nutrition_agent():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        return

    print("--- Testing ReAct Agent with Gemini ---")
    try:
        provider = GeminiProvider(model_name="gemini-3.5-flash", api_key=api_key)
        agent = ReActAgent(llm=provider)
        
        user_context = {
            "id": "user_1",
            "name": "Nguyễn Văn A",
            "goal": "build_muscle",
            "target_calories": 2700
        }

        # Test case 1: Recommend menu
        query = "Hãy lập thực đơn ăn uống gợi ý cho cả ngày của tôi dựa trên mục tiêu cơ thể."
        print(f"\nUser Query 1: {query}\n")
        result = agent.run(user_input=query, user_context=user_context)
        
        print("\n=== AGENT STEPS (ReAct Trace 1) ===")
        for step in result["history"]:
            print(f"Step {step['step']}:")
            if step["thought"]:
                print(f"  Thought: {step['thought']}")
            if step["action"]:
                print(f"  Action: {step['action']}")
            if step["observation"]:
                print(f"  Observation: {step['observation']}")
            if step["final_answer"]:
                print(f"  Final Answer: {step['final_answer']}")
            print("-" * 40)
            
        print(f"\n=== FINAL ANSWER 1 ===\n{result['final_answer']}")

        # Test case 2: Recommend menu with preferred dishes
        query2 = "Tôi muốn ăn Phở bò hôm nay. Hãy lập thực đơn ăn uống gợi ý cho cả ngày của tôi."
        print(f"\nUser Query 2: {query2}\n")
        result2 = agent.run(user_input=query2, user_context=user_context)
        
        print("\n=== AGENT STEPS (ReAct Trace 2) ===")
        for step in result2["history"]:
            print(f"Step {step['step']}:")
            if step["thought"]:
                print(f"  Thought: {step['thought']}")
            if step["action"]:
                print(f"  Action: {step['action']}")
            if step["observation"]:
                print(f"  Observation: {step['observation']}")
            if step["final_answer"]:
                print(f"  Final Answer: {step['final_answer']}")
            print("-" * 40)
            
        print(f"\n=== FINAL ANSWER 2 ===\n{result2['final_answer']}")
        
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")

if __name__ == "__main__":
    test_nutrition_agent()
