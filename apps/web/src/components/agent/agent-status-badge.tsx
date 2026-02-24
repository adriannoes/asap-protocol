'use client';

import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';

interface AgentStatusBadgeProps {
    endpoint: string;
    skipReachabilityCheck?: boolean;
    /** Size variant: 'sm' for dashboard cards, 'default' for agent detail. */
    size?: 'sm' | 'default';
}

export function AgentStatusBadge({
    endpoint,
    skipReachabilityCheck,
    size = 'default',
}: AgentStatusBadgeProps) {
    const [status, setStatus] = useState<'pending' | 'online' | 'offline'>('pending');

    useEffect(() => {
        if (skipReachabilityCheck) return;
        let isMounted = true;
        const check = async () => {
            if (!endpoint) {
                if (isMounted) setStatus('offline');
                return;
            }
            try {
                const res = await fetch(`/api/proxy/check?url=${encodeURIComponent(endpoint)}`);
                const data = (await res.json()) as { ok?: boolean };
                if (isMounted) setStatus(data.ok ? 'online' : 'offline');
            } catch {
                if (isMounted) setStatus('offline');
            }
        };
        check();
        return () => {
            isMounted = false;
        };
    }, [endpoint, skipReachabilityCheck]);

    const sizeClass = size === 'sm' ? 'text-[10px] px-2 py-0' : 'text-xs';

    if (skipReachabilityCheck) {
        return (
            <Badge
                variant="outline"
                className={`${sizeClass} bg-muted text-muted-foreground border-muted-foreground/30`}
            >
                Demo
            </Badge>
        );
    }
    if (status === 'pending') {
        return (
            <Badge
                variant="outline"
                className={`${sizeClass} bg-muted text-muted-foreground border-muted-foreground/30 gap-1`}
            >
                <Loader2 className="w-3 h-3 animate-spin" /> Checking
            </Badge>
        );
    }
    if (status === 'online') {
        return (
            <Badge
                variant="outline"
                className={`${sizeClass} bg-emerald-500/10 text-emerald-500 border-emerald-500/20`}
            >
                Online
            </Badge>
        );
    }
    return (
        <Badge
            variant="outline"
            className={`${sizeClass} bg-red-500/10 text-red-500 border-red-500/20`}
        >
            Offline
        </Badge>
    );
}
