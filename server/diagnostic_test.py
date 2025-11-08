# Quick Diagnostic Script for Duplicate User Issue

## Run this to test the face recognition flow

```python
import requests
import base64
import sys

def test_face_recognition(image_path):
    """Test the face recognition flow to find duplicate user issue"""
    
    BASE_URL = "http://localhost:8000/api/v1"
    
    # Load image
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()
    
    print("=" * 70)
    print("FACE RECOGNITION DUPLICATE USER DIAGNOSTIC TEST")
    print("=" * 70)
    
    # TEST 1: First registration
    print("\n📝 TEST 1: First call to /viewer (should create new user)")
    print("-" * 70)
    
    response1 = requests.post(
        f"{BASE_URL}/viewer",
        data={
            "image_base64": image_base64,
            "start_time": "2025-11-09T10:00:00",
            "end_time": "2025-11-09T10:05:00",
            "duration": 300,
            "org_id": "default_org"
        }
    )
    
    if response1.status_code == 201:
        data1 = response1.json()["data"]
        user_id_1 = data1["user_id"]
        face_id_1 = data1["face_id"]
        session_id_1 = data1["session_id"]
        
        print(f"✅ Status: {response1.status_code} Created")
        print(f"   User ID:    {user_id_1}")
        print(f"   Face ID:    {face_id_1}")
        print(f"   Session ID: {session_id_1}")
    else:
        print(f"❌ Failed: {response1.status_code}")
        print(f"   Error: {response1.text}")
        return
    
    # TEST 2: Track (should recognize)
    print("\n🔍 TEST 2: Call /track (should recognize the user from TEST 1)")
    print("-" * 70)
    
    response_track = requests.post(
        f"{BASE_URL}/track",
        data={
            "image_base64": image_base64,
            "org_id": "default_org"
        }
    )
    
    if response_track.status_code == 200:
        track_data = response_track.json()["data"]
        detected_user = track_data["user_id"]
        confidence = track_data.get("confidence", 0)
        visit_count = track_data.get("visit_count", 0)
        
        print(f"✅ Status: {response_track.status_code} OK")
        print(f"   Detected User: {detected_user}")
        print(f"   Confidence:    {confidence}")
        print(f"   Visit Count:   {visit_count}")
        
        if detected_user == user_id_1:
            print(f"   ✅ MATCH: Same user recognized!")
        else:
            print(f"   ❌ MISMATCH: Different user!")
            print(f"      Expected: {user_id_1}")
            print(f"      Got:      {detected_user}")
    else:
        print(f"❌ Failed: {response_track.status_code}")
        print(f"   Error: {response_track.text}")
    
    # TEST 3: Second registration (should reuse user)
    print("\n🔄 TEST 3: Second call to /viewer (should REUSE user from TEST 1)")
    print("-" * 70)
    
    response2 = requests.post(
        f"{BASE_URL}/viewer",
        data={
            "image_base64": image_base64,
            "start_time": "2025-11-09T15:00:00",
            "end_time": "2025-11-09T15:10:00",
            "duration": 600,
            "org_id": "default_org"
        }
    )
    
    if response2.status_code == 201:
        data2 = response2.json()["data"]
        user_id_2 = data2["user_id"]
        face_id_2 = data2["face_id"]
        session_id_2 = data2["session_id"]
        
        print(f"✅ Status: {response2.status_code} Created")
        print(f"   User ID:    {user_id_2}")
        print(f"   Face ID:    {face_id_2}")
        print(f"   Session ID: {session_id_2}")
        
        # Check if user was reused
        if user_id_2 == user_id_1:
            print(f"\n   ✅ SUCCESS: Same user reused!")
            print(f"      User:    {user_id_1} (consistent)")
            
            if face_id_2 == face_id_1:
                print(f"      Face:    {face_id_1} (reused)")
            else:
                print(f"      Face:    Created new face ID (unexpected)")
            
            if session_id_2 != session_id_1:
                print(f"      Session: New session created ✅")
            else:
                print(f"      Session: Same session (unexpected)")
                
        else:
            print(f"\n   ❌ FAILURE: Different user created (duplicate!)")
            print(f"      First user:  {user_id_1}")
            print(f"      Second user: {user_id_2}")
            print(f"\n   🐛 BUG CONFIRMED: Face not recognized on second /viewer call")
    else:
        print(f"❌ Failed: {response2.status_code}")
        print(f"   Error: {response2.text}")
    
    # TEST 4: Third registration (stress test)
    print("\n🔄 TEST 4: Third call to /viewer (should STILL reuse user)")
    print("-" * 70)
    
    response3 = requests.post(
        f"{BASE_URL}/viewer",
        data={
            "image_base64": image_base64,
            "start_time": "2025-11-09T20:00:00",
            "end_time": "2025-11-09T20:15:00",
            "duration": 900,
            "org_id": "default_org"
        }
    )
    
    if response3.status_code == 201:
        data3 = response3.json()["data"]
        user_id_3 = data3["user_id"]
        
        print(f"✅ Status: {response3.status_code} Created")
        print(f"   User ID: {user_id_3}")
        
        if user_id_3 == user_id_1:
            print(f"   ✅ User reused consistently")
        else:
            print(f"   ❌ Another duplicate created!")
    
    # SUMMARY
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    users = [user_id_1]
    if 'user_id_2' in locals():
        users.append(user_id_2)
    if 'user_id_3' in locals():
        users.append(user_id_3)
    
    unique_users = set(users)
    
    print(f"Total API calls:    {len(users) + 1} (/viewer: {len(users)}, /track: 1)")
    print(f"Unique users created: {len(unique_users)}")
    
    if len(unique_users) == 1:
        print(f"\n✅ PASS: All calls used the same user")
        print(f"   User ID: {user_id_1}")
        print(f"   Face recognition working correctly!")
    else:
        print(f"\n❌ FAIL: Multiple users created for same face")
        for i, user in enumerate(users, 1):
            print(f"   Call {i}: {user}")
        print(f"\n🐛 ROOT CAUSE: recognize_face() not finding existing face")
        print(f"   • Check worker logs for face storage")
        print(f"   • Verify user_id format in create_user() call")
        print(f"   • Check if face cache is updated after create_user()")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnostic_test.py <path_to_image>")
        print("Example: python diagnostic_test.py test_face.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    test_face_recognition(image_path)
```

## How to Use

1. **Save this script** as `diagnostic_test.py`

2. **Install requests** if needed:
```bash
pip install requests
```

3. **Run the test**:
```bash
python diagnostic_test.py path/to/your/test_image.jpg
```

4. **Check the output** - it will clearly show:
   - ✅ If face recognition is working (same user reused)
   - ❌ If there's a bug (multiple users created)

## Example Output (Bug Case)

```
==============================================================
FACE RECOGNITION DUPLICATE USER DIAGNOSTIC TEST
==============================================================

📝 TEST 1: First call to /viewer (should create new user)
--------------------------------------------------------------
✅ Status: 201 Created
   User ID:    viewer_813156ee-c11c-4d16-b9d6-4278b88bab9a
   Face ID:    0d962dd8-0292-4899-ace3-813935cccee1
   Session ID: 9

🔍 TEST 2: Call /track (should recognize the user from TEST 1)
--------------------------------------------------------------
✅ Status: 200 OK
   Detected User: viewer_813156ee-c11c-4d16-b9d6-4278b88bab9a
   Confidence:    0.95
   Visit Count:   1
   ✅ MATCH: Same user recognized!

🔄 TEST 3: Second call to /viewer (should REUSE user from TEST 1)
--------------------------------------------------------------
✅ Status: 201 Created
   User ID:    viewer_a2156771-2302-447c-a292-513559daaaf0
   Face ID:    90764140-1ea7-48d1-b6f9-fcb092fa83fd
   Session ID: 10

   ❌ FAILURE: Different user created (duplicate!)
      First user:  viewer_813156ee-c11c-4d16-b9d6-4278b88bab9a
      Second user: viewer_a2156771-2302-447c-a292-513559daaaf0

   🐛 BUG CONFIRMED: Face not recognized on second /viewer call

==============================================================
SUMMARY
==============================================================
Total API calls:    4 (/viewer: 3, /track: 1)
Unique users created: 3

❌ FAIL: Multiple users created for same face
   Call 1: viewer_813156ee-c11c-4d16-b9d6-4278b88bab9a
   Call 2: viewer_a2156771-2302-447c-a292-513559daaaf0
   Call 3: viewer_0efd603f-6616-4363-8c27-0ddc573fd540

🐛 ROOT CAUSE: recognize_face() not finding existing face
   • Check worker logs for face storage
   • Verify user_id format in create_user() call
   • Check if face cache is updated after create_user()
```

## What to Check Based on Results

### If TEST 2 (/track) Works but TEST 3 (/viewer) Fails

**This means**:
- Face IS being stored in worker cache ✅
- `/track` can find it ✅
- But `/viewer` can't find it ❌

**Action**: The bug is in `/viewer` endpoint logic. Check if there's a difference in how `/viewer` and `/track` call `recognize_face()`.

### If Both TEST 2 and TEST 3 Fail

**This means**:
- Face is NOT being stored properly ❌
- Worker cache is not updated after `create_user()` ❌

**Action**: Check the worker logs when `create_user()` is called. The face might not be persisted to the recognition database.

### If All Tests Pass

**This means**:
- Everything works correctly! ✅
- The issue might be with:
  - Different images being used
  - Different org_id values
  - Cached responses
