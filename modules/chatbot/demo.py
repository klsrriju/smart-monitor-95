import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_query(prompt: str):
    print(f"\n--- Testing Query: '{prompt}' ---")
    try:
        res = requests.post(
            f"{BASE_URL}/api/v1/chat",
            json={"query": prompt}
        )
        if res.status_code == 200:
            data = res.json()
            print(f"Detected Intent : {data['intent']}")
            print(f"Retrieved Data  : {json.dumps(data['context_data'], indent=2)}")
            print(f"Bot Response    :\n{data['response']}")
        else:
            print(f"Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    # Sample Test Queries
    test_query("What is the attendance status for R. Meena?")
    test_query("Check camera status for CAM-002")
    test_query("Are there any anomalies reported for project PS-26095?")