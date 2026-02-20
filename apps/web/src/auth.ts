import NextAuth from 'next-auth';
import GitHub from 'next-auth/providers/github';

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
        session({ session, token }) {
            if (typeof token.id === 'string' && session.user) {
                session.user.id = token.id;
            }
            if (typeof token.username === "string" && session.user) {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (session.user as any).username = token.username;
            }
            if (typeof token.accessToken === "string") {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (session as any).accessToken = token.accessToken;
            }
            return session;
        },
    },
    pages: { signIn: '/' },
});
