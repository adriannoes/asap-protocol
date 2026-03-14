"use server";

import { signIn, signOut } from "@/auth";
import { AGENT_BUILDER_URL_WITH_FROM } from "@/lib/agent-builder-url";

export async function signInWithGitHub() {
  await signIn("github");
}

export async function signInWithGitHubForAgentBuilder() {
  await signIn("github", {
    redirectTo: AGENT_BUILDER_URL_WITH_FROM,
  });
}

export async function signOutAction() {
  await signOut({ redirectTo: "/" });
}
