/** Upgrade compatibility ONLY.
 * Previous v0.7 installations may retain this filename when copying v0.8 over
 * the old folder. No Supabase package, network service, or credentials are used.
 * Actual authentication is implemented in local-auth.ts and FastAPI/PostgreSQL.
 */
export {localAuthClient as supabaseClient, accountApi, apiOrigin} from './local-auth';
