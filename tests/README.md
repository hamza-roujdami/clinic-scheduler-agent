# Tests

Test files for the clinic scheduler agents.

## Available Tests

### Sequential Booking Workflow
```bash
python tests/test_sequential_booking.py
```

Tests the production-ready sequential orchestration pattern that enforces a 3-step booking flow:
1. **Verification Agent** - Validates Emirates ID and phone number
2. **Availability Agent** - Checks doctor schedule and available slots
3. **Booking Agent** - Creates the final appointment

This demonstrates how Sequential Orchestration ensures steps cannot be skipped, which is critical for production healthcare booking workflows.