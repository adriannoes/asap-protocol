import "next-auth";

declare module "next-auth" {
    interface User {
        username?: string;
    }

    /**
     * Returned by `useSession`, `getSession` and received as a prop on the `SessionProvider` React Context
     */
    interface Session {
        user: {
            id: string;
            username?: string;
            name?: string;
            email?: string;
            image?: string;
        };
        /** GitHub OAuth access token; server-side only, from JWT callback. */
        accessToken?: string;
    }

    interface Profile {
        login?: string;
    }
}

declare module "next-auth/jwt" {
    /** Returned by the `jwt` callback and `getToken`, when using JWT sessions */
    interface JWT {
        id?: string;
        username?: string;
        accessToken?: string;
    }
}
