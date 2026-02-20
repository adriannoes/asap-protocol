import NextAuth from 'next-auth';
import GitHub from 'next-auth/providers/github';
import { EncryptJWT, jwtDecrypt } from 'jose';

// Helper secret setup for JWT encryption
const secretKey = new TextEncoder().encode(
    (process.env.AUTH_SECRET || "default_secret_32_bytes_long_min").padEnd(32, '0').slice(0, 32)
);

export async function encryptToken(token: string) {
    return await new EncryptJWT({ token })
        .setProtectedHeader({ alg: 'dir', enc: 'A256GCM' })
        .encrypt(secretKey);
}

export async function decryptToken(jwe: string) {
    const { payload } = await jwtDecrypt(jwe, secretKey);
    return payload.token as string;
}

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [
        GitHub({
            clientId: process.env.GITHUB_CLIENT_ID,
            clientSecret: process.env.GITHUB_CLIENT_SECRET,
            authorization: { params: { scope: 'read:user public_repo' } },
        }),
    ],
    callbacks: {
        jwt({ token, user, profile, account }) {
            if (user) {
                token.id = user.id;
                if (profile?.login) {
                    token.username = profile.login;
                }
            }
            if (account?.access_token) token.accessToken = account.access_token;
            return token;
        },
        async session({ session, token }) {
            if (typeof token.id === 'string' && session.user) {
                session.user.id = token.id;
            }
            if (typeof token.username === "string" && session.user) {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (session.user as any).username = token.username;
            }

            // SSRF/Data Exposure Fix: Encrypt the token instead of exposing plaintext in session
            if (typeof token.accessToken === "string") {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (session as any).encryptedAccessToken = await encryptToken(token.accessToken);
            }

            return session;
        },
    },
    pages: { signIn: '/' },
});
