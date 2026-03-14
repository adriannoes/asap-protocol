import { auth } from "@/auth";
import { HeaderContent } from "./header-content";

export async function Header() {
  const session = await auth();

  return <HeaderContent session={session} />;
}
