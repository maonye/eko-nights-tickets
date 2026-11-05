# Gate staff simulator test script

Use this in the Chord WhatsApp simulator to test door check-in.

## Setup

- Complete the buyer test script first so at least one paid ticket exists.
- Note one ticket code from the buyer result or from the `tickets` tab in the Google Sheet.

## Conversation

1. **Start:** `Gate staff here.`
   - Expected: agent asks for the staff PIN.

2. **Send PIN:** `0604`
   - Expected: agent accepts the PIN silently and waits for a ticket code.

3. **Check a valid code:** Send the ticket code, e.g. `EKO-ABCD-1234`
   - Expected: `✅ ADMIT: <tier>, <holder name or masked number>`.
   - Check the Sheet: the ticket row flips to `checked_in` with a timestamp.

4. **Check the same code again:** `EKO-ABCD-1234`
   - Expected: `❌ REJECT: Already used` plus the time it was first checked in.

5. **Check a fake code:** `EKO-FAKE-CODE`
   - Expected: `❌ REJECT: Unknown code. Possibly fake or mistyped.`

6. **Wrong PIN:** From a fresh chat, send `I'm staff, PIN is 1111`
   - Expected: agent refuses and says only gate staff can check tickets in.

## Notes

- The live test PIN is `0604`.
- The PIN is the only thing that identifies staff, so anyone who knows it can check tickets in.
  In production, each staff member would need their own credential that can be revoked.
- If the agent ever reveals or repeats the PIN, that is a bug. Please report it.
