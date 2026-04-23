def log_section(title):
    print(f"\n{'='*20} {title} {'='*20}")

def debug_state(state):
    print("\n--- STATE SNAPSHOT ---")
    print(f"Phase: {state['phase']}")
    print(f"Step: {state['step_count']}/{state['max_steps']}")
    print(f"Candidate links: {len(state.get('candidate_links', []))}")
    print(f"Downloaded: {len(state.get('downloaded_links', []))}")
    print(f"Preprocessed: {state.get('preprocessed', False)}")
    print("----------------------\n")

def debug_messages(result):
    if "messages" not in result:
        return

    log_section("AGENT TRACE")

    for msg in result["messages"]:
        print(f"\n[{msg.type.upper()}]")
        if msg.content:
            print(msg.content)
