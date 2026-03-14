'use client';

import { useState, useEffect } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import {
    flexRender,
    getCoreRowModel,
    getFilteredRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    useReactTable,
    type ColumnDef,
    type ColumnFiltersState,
    type SortingState,
    type VisibilityState,
} from '@tanstack/react-table';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DataTableProps<TData, TValue> {
    columns: ColumnDef<TData, TValue>[];
    data: TData[];
    searchKey?: string;
}

const MOBILE_HIDDEN_COLUMNS = new Set<string>(['version', 'skills']);

export function DataTable<TData, TValue>({
    columns,
    data,
    searchKey,
}: DataTableProps<TData, TValue>) {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();
    const initialSearch = searchParams.get('search') ?? '';
    const [search, setSearch] = useState(initialSearch);
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>(
        searchKey && initialSearch ? [{ id: searchKey, value: initialSearch }] : []
    );
    const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

    useEffect(() => {
        const urlSearch = searchParams.get('search') ?? '';
        setSearch(urlSearch);
        if (searchKey) {
            setColumnFilters((prev) => {
                const rest = prev.filter((f) => f.id !== searchKey);
                return urlSearch ? [...rest, { id: searchKey, value: urlSearch }] : rest;
            });
        }
    }, [searchParams, searchKey]);

    // Debounce URL update to avoid server roundtrip on every keystroke
    useEffect(() => {
        const t = setTimeout(() => {
            const params = new URLSearchParams(searchParams.toString());
            if (search) params.set('search', search);
            else params.delete('search');
            const qs = params.toString();
            const newSearch = params.get('search') ?? '';
            const currentSearch = searchParams.get('search') ?? '';
            if (newSearch !== currentSearch) {
                router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
            }
        }, 300);
        return () => clearTimeout(t);
    }, [search, pathname, searchParams, router]);

    const updateSearch = (value: string) => {
        setSearch(value);
        if (searchKey) {
            setColumnFilters((prev) => {
                const rest = prev.filter((f) => f.id !== searchKey);
                return value ? [...rest, { id: searchKey, value }] : rest;
            });
        }
    };

    // eslint-disable-next-line react-hooks/incompatible-library
    const table = useReactTable({
        data,
        columns,
        onSortingChange: setSorting,
        onColumnFiltersChange: (updater) => {
            const next = typeof updater === 'function' ? updater(columnFilters) : updater;
            setColumnFilters(next);
            const searchFilter = next.find((f) => f.id === searchKey);
            if (searchKey && searchFilter?.value !== undefined) {
                setSearch(String(searchFilter.value));
                const params = new URLSearchParams(searchParams.toString());
                if (searchFilter.value) params.set('search', String(searchFilter.value));
                else params.delete('search');
                const qs = params.toString();
                router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
            }
        },
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        onColumnVisibilityChange: (updater) =>
            setColumnVisibility((prev) => (typeof updater === 'function' ? updater(prev) : updater)),
        state: {
            sorting,
            columnFilters,
            columnVisibility,
        },
    });

    const isMobileHidden = (columnId: string) => MOBILE_HIDDEN_COLUMNS.has(columnId);

    return (
        <div data-testid="data-table" className="w-full space-y-4">
            {searchKey && (
                <Input
                    data-testid="data-table-search"
                    placeholder="Search agents..."
                    value={search}
                    onChange={(e) => updateSearch(e.target.value)}
                    className="w-full sm:max-w-sm"
                />
            )}
            <div className="overflow-x-auto rounded-md border">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => {
                                    const sortDir = header.column.getIsSorted();
                                    const ariaSort =
                                        sortDir === 'asc'
                                            ? 'ascending'
                                            : sortDir === 'desc'
                                              ? 'descending'
                                              : undefined;
                                    return (
                                        <TableHead
                                            key={header.id}
                                            {...(ariaSort ? { ariaSort } : {})}
                                            data-sort-direction={ariaSort}
                                            className={cn(
                                                isMobileHidden(header.column.id) && 'hidden sm:table-cell'
                                            )}
                                        >
                                            {header.isPlaceholder
                                                ? null
                                                : flexRender(
                                                      header.column.columnDef.header,
                                                      header.getContext()
                                                  )}
                                        </TableHead>
                                    );
                                })}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow
                                    key={row.id}
                                    data-state={row.getIsSelected() && 'selected'}
                                    className="hover:bg-muted/50"
                                >
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell
                                            key={cell.id}
                                            className={cn(
                                                isMobileHidden(cell.column.id) && 'hidden sm:table-cell'
                                            )}
                                        >
                                            {flexRender(
                                                cell.column.columnDef.cell,
                                                cell.getContext()
                                            )}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length}
                                    className="h-24 text-center"
                                >
                                    No results.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
            <div
                data-testid="data-table-pagination"
                className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
            >
                <p className="text-sm text-muted-foreground">
                    {table.getFilteredRowModel().rows.length} row(s)
                </p>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => table.previousPage()}
                        disabled={!table.getCanPreviousPage()}
                        className="flex-1 sm:flex-initial"
                    >
                        Previous
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => table.nextPage()}
                        disabled={!table.getCanNextPage()}
                        className="flex-1 sm:flex-initial"
                    >
                        Next
                    </Button>
                </div>
            </div>
        </div>
    );
}
