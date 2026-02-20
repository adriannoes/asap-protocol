import NextAuth from 'next-auth';
import GitHub from 'next-auth/providers/github';

export const { handlers, auth, signIn, signOut } = NextAuth({
    providers: [
        GitHub({
            clientId: process.env.GITHUB_CLIENT_ID,
            clientSecret: process.env.GITHUB_CLIENT_SECRET,
            // Provide an empty array for local and required for NextAuth GitHub provider typing
            // We will only read public profile information and repo creation ability for registry PRs
            authorization: { params: { scope: 'read:user public_repo' } },
        }),
    ],
    callbacks: {
        jwt({ token, user, profile }) {
            if (user) {
                token.id = user.id;
                // Optionally attach GitHub username if we need it
                if (profile?.login) {
                    token.username = profile.login;
                }
            }
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
            return session;
        },
    },
    pages: {
        signIn: '/', // We will open a modal or direct login on the landing page/header
    },
});
