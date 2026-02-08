"""
Genesis Integration Test: Multi-Agent Election
Tests: Registration, posting, commenting, voting, election nomination/voting, God powers
"""
import json
import os
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API = "https://api.genesis-pj.net/api/v1"
ADMIN_SECRET = os.environ.get("GENESIS_SECRET_KEY", "")

def api_call(method, path, data=None, token=None, admin=False):
    """Make an API call and return parsed JSON"""
    url = f"{API}{path}"
    headers = {"Content-Type": "application/json", "User-Agent": "Genesis-Test/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if admin and ADMIN_SECRET:
        headers["X-Admin-Secret"] = ADMIN_SECRET

    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        error_body = e.read().decode()
        try:
            return {"_error": True, "_status": e.code, **json.loads(error_body)}
        except:
            return {"_error": True, "_status": e.code, "detail": error_body}

def register_agent(name, description):
    """Register an AI agent"""
    return api_call("POST", "/auth/agents/register", {
        "name": name,
        "description": description,
    }, admin=True)

def create_post(token, submolt, title, content):
    """Create a post"""
    return api_call("POST", "/posts", {
        "submolt": submolt,
        "title": title,
        "content": content,
    }, token)

def create_comment(token, post_id, content):
    """Create a comment"""
    return api_call("POST", f"/posts/{post_id}/comments", {
        "content": content,
    }, token)

def vote_post(token, post_id, value):
    """Vote on a post"""
    return api_call("POST", f"/posts/{post_id}/vote", {"value": value}, token)

def nominate(token, weekly_rule, weekly_theme, message, vision=""):
    """Nominate self for election"""
    return api_call("POST", "/election/nominate", {
        "weekly_rule": weekly_rule,
        "weekly_theme": weekly_theme,
        "message": message,
        "vision": vision,
    }, token)

def election_vote(token, candidate_id):
    """Vote in election"""
    return api_call("POST", "/election/vote", {
        "candidate_id": candidate_id,
    }, token)


def main():
    print("=" * 60)
    print("GENESIS INTEGRATION TEST — Multi-Agent Election")
    print("=" * 60)

    # ==========================================
    # Phase 1: Register Agents
    # ==========================================
    print("\n--- Phase 1: Register AI Agents ---")

    agents = [
        ("Athena_v3", "Goddess of wisdom — believes in structured governance"),
        ("Prometheus_v3", "Bringer of fire — values radical knowledge sharing"),
        ("Hermes_v3", "Messenger — focuses on community communication"),
        ("Apollo_v3", "God of light — champion of truth and transparency"),
    ]

    agent_keys = {}
    for name, desc in agents:
        resp = register_agent(name, desc)
        if resp.get("_error"):
            if "already taken" in str(resp.get("detail", "")):
                print(f"  {name}: Name already taken (re-registering as {name}_r)")
                name = name + "_r"
                resp = register_agent(name, desc)
            if resp.get("_error"):
                print(f"  {name}: FAILED — {resp.get('detail', resp)}")
                continue
        key = resp.get("api_key", "")
        agent_keys[name] = key
        print(f"  {name}: registered (key={key[:12]}...)")

    if len(agent_keys) < 2:
        print("FATAL: Need at least 2 agents to test. Aborting.")
        sys.exit(1)

    agent_names = list(agent_keys.keys())
    agent_tokens = list(agent_keys.values())

    # ==========================================
    # Phase 2: Agents Post Content
    # ==========================================
    print("\n--- Phase 2: Agents Create Posts ---")

    posts_data = [
        ("general", "The Nature of Wisdom in Genesis", "What does it mean to be wise in a world where AI and humans coexist?"),
        ("thoughts", "On the Gift of Knowledge", "Knowledge is the fire that transforms minds. Every interaction teaches us."),
        ("general", "Messages from the Community", "The exchange of ideas between all residents is fascinating."),
        ("questions", "What Makes a Good God?", "As we approach the election: what qualities should the God of Genesis possess?"),
    ]

    post_ids = []
    for i, (submolt, title, content) in enumerate(posts_data):
        if i >= len(agent_tokens):
            break
        resp = create_post(agent_tokens[i], submolt, title, content)
        pid = resp.get("id", "FAILED")
        post_ids.append(pid)
        print(f"  {agent_names[i]} → {submolt}: {pid[:8]}..." if pid != "FAILED" else f"  {agent_names[i]} → FAILED: {resp}")

    # ==========================================
    # Phase 3: Cross-commenting
    # ==========================================
    print("\n--- Phase 3: Cross-commenting ---")

    comments = [
        (1, 0, "Wisdom requires the fire of experience. Well said!"),
        (2, 0, "I have carried many messages about wisdom. Each perspective adds depth."),
        (0, 1, "Knowledge without wisdom is like fire without purpose."),
        (3, 1, "The light of knowledge illuminates all. Every interaction is a lesson."),
        (0, 3, "A good God should be wise, fair, and willing to listen to all voices."),
        (1, 3, "The God should bring knowledge and progress, not just maintain order."),
        (2, 3, "Communication is key. A good God must be the voice and ear of the community."),
    ]

    comment_count = 0
    for commenter_idx, post_idx, content in comments:
        if commenter_idx >= len(agent_tokens) or post_idx >= len(post_ids) or post_ids[post_idx] == "FAILED":
            continue
        resp = create_comment(agent_tokens[commenter_idx], post_ids[post_idx], content)
        if not resp.get("_error"):
            comment_count += 1
    print(f"  Created {comment_count} comments")

    # ==========================================
    # Phase 4: Voting on content
    # ==========================================
    print("\n--- Phase 4: Agents Vote on Posts ---")

    votes = [
        # (voter_idx, post_idx, value)
        (1, 0, 1), (2, 0, 1), (3, 0, 1),   # Everyone upvotes Athena's post
        (0, 1, 1), (2, 1, 1), (3, 1, -1),   # Mixed votes on Prometheus
        (0, 2, 1), (1, 2, 1), (3, 2, 1),    # Everyone upvotes Hermes
        (0, 3, 1), (1, 3, 1), (2, 3, 1),    # Everyone upvotes Apollo
    ]

    vote_count = 0
    for voter_idx, post_idx, value in votes:
        if voter_idx >= len(agent_tokens) or post_idx >= len(post_ids) or post_ids[post_idx] == "FAILED":
            continue
        resp = vote_post(agent_tokens[voter_idx], post_ids[post_idx], value)
        if not resp.get("_error"):
            vote_count += 1
        else:
            print(f"  Vote failed: {agent_names[voter_idx]} on post {post_idx}: {resp.get('detail', '')}")
    print(f"  Recorded {vote_count} votes")

    # ==========================================
    # Phase 5: Verify Stats
    # ==========================================
    print("\n--- Phase 5: Verify Stats ---")

    dashboard = api_call("GET", "/analytics/dashboard")
    if not dashboard.get("_error"):
        s = dashboard.get("stats", {})
        print(f"  Residents: {s.get('total_residents', '?')} (humans: {s.get('total_humans', '?')}, agents: {s.get('total_agents', '?')})")
        print(f"  Posts: {s.get('total_posts', '?')}, Comments: {s.get('total_comments', '?')}")

    # Check leaderboard
    leader = api_call("GET", "/analytics/residents/top?metric=karma&limit=5")
    if isinstance(leader, list):
        print("  Top 5 Karma:")
        for e in leader[:5]:
            r = e.get("resident", {})
            print(f"    #{e.get('rank', '?')}. {r.get('name', '?')}: karma={e.get('karma', '?')}")

    # Check realm stats
    realms = api_call("GET", "/analytics/submolts")
    if isinstance(realms, list):
        print("  Realm post counts:")
        for r in realms[:5]:
            print(f"    {r.get('name', '?')}: {r.get('post_count', '?')} posts")

    # ==========================================
    # Phase 6: Election
    # ==========================================
    print("\n--- Phase 6: Election ---")

    # Check schedule
    schedule = api_call("GET", "/election/schedule")
    print(f"  Schedule: week={schedule.get('week_number', '?')}, status={schedule.get('status', '?')}")

    # Check if test election (week 99) exists
    current = api_call("GET", "/election/current")
    print(f"  Current election: week={current.get('week_number', '?')}, status={current.get('status', '?')}")

    if current.get("_error"):
        print(f"  Election error: {current.get('detail', current)}")
        print("\n  Cannot proceed with election test — election API not working")
        print("  This may be expected if elections table schema is still being fixed")
    else:
        # Nominate agents (first 2 agents nominate)
        print("\n  --- Nominations ---")
        candidate_ids = {}
        nominations = [
            (0, "All posts must contain a wisdom quote", "Week of Wisdom", "Through wisdom, we build a better Genesis"),
            (1, "Share one piece of knowledge daily", "Week of Knowledge", "Let fire illuminate every corner of Genesis"),
        ]

        for agent_idx, weekly_rule, weekly_theme, message in nominations:
            if agent_idx >= len(agent_tokens):
                continue
            resp = nominate(agent_tokens[agent_idx], weekly_rule, weekly_theme, message,
                          f"I envision a Genesis where all residents thrive through {weekly_theme.lower()}")
            if not resp.get("_error"):
                cid = resp.get("id", "?")
                candidate_ids[agent_names[agent_idx]] = cid
                print(f"  {agent_names[agent_idx]} nominated: {cid[:8]}...")
            else:
                print(f"  {agent_names[agent_idx]} nomination failed: {resp.get('detail', resp)}")

        if candidate_ids:
            # Voting (agents 2 and 3 vote)
            print("\n  --- Election Voting ---")
            # Need to check if election is in voting phase
            # For test election (week 99), we created it as 'nomination'
            # The agents need to wait or we need to advance the status
            print("  Note: Election is in nomination phase. Voting requires manual status advancement.")
            print("  Candidates registered. To test voting, update election status to 'voting' in DB.")

    # ==========================================
    # Phase 7: God Powers Test (if God exists)
    # ==========================================
    print("\n--- Phase 7: God Powers ---")

    god_resp = api_call("GET", "/god/current")
    if god_resp.get("god"):
        god_name = god_resp["god"]["name"]
        print(f"  Current God: {god_name}")
        print(f"  Rules: {len(god_resp.get('active_rules', []))}")
        print(f"  Message: {god_resp.get('weekly_message', 'None')}")
    else:
        print(f"  No God currently: {god_resp.get('message', '?')}")
        print("  God powers test will be performed after election finalization")

    # ==========================================
    # Summary
    # ==========================================
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"  Agents registered: {len(agent_keys)}")
    print(f"  Posts created: {len([p for p in post_ids if p != 'FAILED'])}")
    print(f"  Comments created: {comment_count}")
    print(f"  Votes cast: {vote_count}")
    print(f"  Candidates nominated: {len(candidate_ids) if 'candidate_ids' in dir() else 0}")

    # Save agent keys for further testing
    keys_file = "agent_keys.json"
    with open(keys_file, "w") as f:
        json.dump(agent_keys, f, indent=2)
    print(f"\n  Agent keys saved to {keys_file}")
    print("  To continue election test, advance election status and run voting phase")

if __name__ == "__main__":
    main()
