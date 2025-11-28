"""
Simple test script to verify the API is working correctly.
Run this after starting the backend server.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

# Sample transcript for testing
SAMPLE_TRANSCRIPT = """
Sarah: Good morning everyone. Let's kick off our Q4 planning session. We need to finalize our roadmap for the next quarter. John, can you start by sharing the engineering capacity?

John: Sure. We have about 40 story points available per sprint. We're planning for 3 sprints in Q4, so roughly 120 points total. We need to allocate some time for technical debt and bug fixes though.

Sarah: Understood. Lisa, what are the design priorities?

Lisa: We need to redesign the dashboard - it's been on the backlog for too long. I'd estimate that at 20 points. We also need to finalize the mobile app design, another 15 points.

Mike: From marketing's perspective, we really need the analytics feature. It's critical for our customer success team. That should be our top priority.

Sarah: Okay, let me summarize what I'm hearing. We have competing priorities. Let me propose this: we allocate 30 points to the analytics feature, 20 to the dashboard redesign, 15 to mobile design, and the remaining 55 points for bug fixes and technical debt.

John: That works for us. We can start with analytics in sprint 1.

Lisa: Dashboard redesign can start in sprint 2 once we have the analytics foundation.

Mike: Great. We need to announce the analytics feature to customers by end of October.

Sarah: Noted. So action items: John, you'll lead the analytics implementation. Lisa, you'll coordinate with John on the design. Mike, you'll prepare the customer announcement. We'll have a sync next week to review the detailed specs.

John: I'll have the technical design doc ready by Friday.

Lisa: And I'll have the design mockups ready by next Wednesday.

Sarah: Perfect. One more thing - we decided to push the mobile redesign to Q1 instead of Q4. This gives us more flexibility.

Mike: Understood. I'll update the roadmap on our website.

Sarah: Great. Let's wrap up. Next meeting is next Tuesday at 10 AM. Thanks everyone.
"""


def test_health():
    """Test health endpoint."""
    print("\n" + "="*60)
    print("Testing Health Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL.replace('/api', '')}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_text_endpoint():
    """Test POST /api/meetings/text endpoint."""
    print("\n" + "="*60)
    print("Testing POST /api/meetings/text")
    print("="*60)
    
    payload = {
        "title": "Q4 Product Planning",
        "language": "en",
        "transcript_text": SAMPLE_TRANSCRIPT
    }
    
    print(f"Sending request with transcript ({len(SAMPLE_TRANSCRIPT)} characters)...")
    print(f"Title: {payload['title']}")
    print(f"Language: {payload['language']}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/meetings/text",
            json=payload,
            timeout=60
        )
        elapsed_time = time.time() - start_time
        
        print(f"\nStatus: {response.status_code}")
        print(f"Time taken: {elapsed_time:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nMeeting ID: {data.get('meeting_id')}")
            print(f"Title: {data.get('title')}")
            print(f"Language: {data.get('language')}")
            
            if data.get('summary'):
                print(f"\nSummary ({len(data['summary']['bullets'])} bullets):")
                for i, bullet in enumerate(data['summary']['bullets'], 1):
                    print(f"  {i}. {bullet}")
            
            if data.get('action_items'):
                print(f"\nAction Items ({len(data['action_items'])} items):")
                for item in data['action_items']:
                    print(f"  - {item['task']}")
                    if item.get('assignee'):
                        print(f"    Assignee: {item['assignee']}")
                    if item.get('deadline'):
                        print(f"    Deadline: {item['deadline']}")
            
            if data.get('decisions'):
                print(f"\nDecisions ({len(data['decisions'])} decisions):")
                for decision in data['decisions']:
                    print(f"  - {decision['decision']}")
                    if decision.get('owner'):
                        print(f"    Owner: {decision['owner']}")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
    
    except requests.exceptions.Timeout:
        print("Error: Request timed out (60 seconds)")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_get_endpoint(meeting_id):
    """Test GET /api/meetings/{id} endpoint."""
    print("\n" + "="*60)
    print(f"Testing GET /api/meetings/{meeting_id}")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/meetings/{meeting_id}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Title: {data.get('title')}")
            print(f"Language: {data.get('language')}")
            print(f"Source: {data.get('source')}")
            print(f"Summary bullets: {len(data.get('summary', {}).get('bullets', []))}")
            print(f"Action items: {len(data.get('action_items', []))}")
            print(f"Decisions: {len(data.get('decisions', []))}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("Meeting Notes Summarizer - API Test Suite")
    print("="*60)
    
    # Test health endpoint
    if not test_health():
        print("\n✗ Backend is not running!")
        print("Please start the backend with: python -m uvicorn app.main:app --reload")
        return
    
    print("\n✓ Backend is running!")
    
    # Test text endpoint
    if test_text_endpoint():
        print("\n✓ Text processing endpoint works!")
        
        # Extract meeting ID from response (we'll need to call again to get it)
        response = requests.post(
            f"{BASE_URL}/meetings/text",
            json={
                "title": "Test Meeting",
                "language": "en",
                "transcript_text": "John: We completed the task. Sarah: Great!"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            meeting_id = response.json().get('meeting_id')
            
            # Test get endpoint
            if test_get_endpoint(meeting_id):
                print(f"\n✓ Get meeting endpoint works!")
            else:
                print(f"\n✗ Get meeting endpoint failed!")
        
    else:
        print("\n✗ Text processing endpoint failed!")
    
    print("\n" + "="*60)
    print("Test Suite Complete")
    print("="*60)


if __name__ == "__main__":
    main()


