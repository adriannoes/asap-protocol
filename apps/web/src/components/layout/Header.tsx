import Link from "next/link";
import { Terminal } from "lucide-react";
import { auth, signIn, signOut } from "@/auth";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export async function Header() {
    const session = await auth();

    return (
        <header className="sticky top-0 z-50 w-full border-b border-zinc-800 bg-zinc-950/80 backdrop-blur supports-[backdrop-filter]:bg-zinc-950/60">
            <div className="container mx-auto px-4 md:px-6 flex h-16 items-center justify-between">

                {/* Logo Left */}
                <div className="flex items-center gap-2">
                    <Link href="/" className="flex items-center gap-2 text-white hover:text-indigo-400 transition-colors">
                        <div className="bg-indigo-500/10 p-1.5 rounded-lg border border-indigo-500/20">
                            <Terminal className="h-5 w-5 text-indigo-400" />
                        </div>
                        <span className="font-bold text-lg tracking-tight">ASAP Protocol</span>
                    </Link>
                </div>

                {/* Center Nav */}
                <nav className="hidden md:flex items-center gap-6">
                    <Link href="/browse" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
                        Registry
                    </Link>
                    <Link href="https://github.com/adriannoes/asap-protocol/tree/main/docs" target="_blank" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
                        Docs
                    </Link>
                </nav>

                {/* Right Auth/Actions */}
                <div className="flex items-center gap-4">
                    {session?.user ? (
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" className="relative h-9 w-9 rounded-full ring-1 ring-zinc-800 hover:ring-indigo-500/50 transition-all">
                                    <Avatar className="h-9 w-9">
                                        <AvatarImage src={session.user.image!} alt={session.user.name || "User"} />
                                        <AvatarFallback className="bg-zinc-900 text-zinc-400">
                                            {session.user.name?.charAt(0) || "U"}
                                        </AvatarFallback>
                                    </Avatar>
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent className="w-56 bg-zinc-950 border-zinc-800 text-zinc-300" align="end" forceMount>
                                <DropdownMenuLabel className="font-normal">
                                    <div className="flex flex-col space-y-1">
                                        <p className="text-sm font-medium leading-none text-white">{session.user.name}</p>
                                        <p className="text-xs leading-none text-zinc-500">
                                            {session.user.email}
                                        </p>
                                    </div>
                                </DropdownMenuLabel>
                                <DropdownMenuSeparator className="bg-zinc-800" />
                                <DropdownMenuItem asChild className="focus:bg-zinc-900 focus:text-white cursor-pointer">
                                    <Link href="/dashboard">Dashboard</Link>
                                </DropdownMenuItem>
                                <DropdownMenuSeparator className="bg-zinc-800" />
                                <DropdownMenuItem className="focus:bg-zinc-900 focus:text-red-400 cursor-pointer p-0">
                                    <form
                                        className="w-full"
                                        action={async () => {
                                            "use server";
                                            await signOut({ redirectTo: "/" });
                                        }}
                                    >
                                        <button className="w-full text-left px-2 py-1.5" type="submit">
                                            Log out
                                        </button>
                                    </form>
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    ) : (
                        <form
                            action={async () => {
                                "use server";
                                await signIn("github");
                            }}
                        >
                            <Button type="submit" variant="outline" className="border-zinc-800 text-zinc-300 hover:bg-zinc-900 hover:text-white">
                                Connect / Login
                            </Button>
                        </form>
                    )}
                </div>

            </div>
        </header>
    );
}
