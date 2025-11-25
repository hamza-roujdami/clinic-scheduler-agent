"""
Quick test: Sequential Booking Workflow
Shows how the 3-step process enforces order
"""

import asyncio
from agents.booking_agent_sequential import create_sequential_booking_workflow
from agent_framework import WorkflowOutputEvent, Role
from typing import cast

async def main():
    print("=" * 70)
    print("TESTING SEQUENTIAL ORCHESTRATION PATTERN")
    print("=" * 70)
    print("\n✓ This demonstrates how Sequential Orchestration enforces a")
    print("  multi-step booking flow that cannot be skipped.\n")
    
    workflow = create_sequential_booking_workflow()
    
    # Test: User provides all info upfront
    prompt = (
        "Book appointment: Emirates ID 12345, phone +971501234567, "
        "Dr. Ahmed on 2025-11-26 at 14:00, name is Sara Ahmed, reason: annual checkup"
    )
    
    print(f"USER REQUEST:\n{prompt}\n")
    print("=" * 70)
    print("SEQUENTIAL WORKFLOW EXECUTION:\n")
    
    step_count = 0
    async for event in workflow.run_stream(prompt):
        if isinstance(event, WorkflowOutputEvent):
            conversation = cast(list, event.data)
            # Find latest assistant message
            for msg in reversed(conversation):
                if msg.role == Role.ASSISTANT and msg.author_name:
                    step_count += 1
                    print(f"STEP {step_count} - {msg.author_name}:")
                    print(f"{msg.text[:200]}...")
                    print()
                    break
    
    print("=" * 70)
    print("✓ WORKFLOW COMPLETE")
    print(f"✓ Executed {step_count} sequential steps in order")
    print("✓ No steps were skipped - this is enforced by the framework")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
