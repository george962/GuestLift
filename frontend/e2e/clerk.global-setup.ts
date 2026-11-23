// Only used when JOURNEY_AUTH_MODE=clerk: fetches a Clerk testing token so bot protection doesn't block the test.
import {clerkSetup} from '@clerk/testing/playwright';
export default async function globalSetup() { await clerkSetup(); }
