"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import type { Ps2AnalysisListItem } from "@/types/analysis";

type SortOption =
  | "satisfaction-low"
  | "satisfaction-high"
  | "date-newest"
  | "date-oldest";

function satisfactionRatio(item: Ps2AnalysisListItem): number {
  const { score, maxScore } = item.partnerSatisfactionScore;
  return maxScore > 0 ? score / maxScore : 0;
}

function sortItems(
  list: Ps2AnalysisListItem[],
  sort: SortOption
): Ps2AnalysisListItem[] {
  const copy = [...list];
  switch (sort) {
    case "satisfaction-low":
      return copy.sort(
        (a, b) =>
          a.partnerSatisfactionScore.score - b.partnerSatisfactionScore.score
      );
    case "satisfaction-high":
      return copy.sort(
        (a, b) =>
          b.partnerSatisfactionScore.score - a.partnerSatisfactionScore.score
      );
    case "date-newest":
      return copy.sort(
        (a, b) =>
          new Date(b.metadata.processedAt).getTime() -
          new Date(a.metadata.processedAt).getTime()
      );
    case "date-oldest":
      return copy.sort(
        (a, b) =>
          new Date(a.metadata.processedAt).getTime() -
          new Date(b.metadata.processedAt).getTime()
      );
    default:
      return copy;
  }
}

export default function Ps2AnalysisResultsPage() {
  const [list, setList] = useState<Ps2AnalysisListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortOption>("satisfaction-low");
  const [issueTypeFilter, setIssueTypeFilter] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch("/api/ps2-analysis")
      .then((res) => {
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
      })
      .then((data: { list?: Ps2AnalysisListItem[] }) => {
        if (cancelled) return;
        setList(data.list ?? []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message ?? "Failed to load");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const issueTypes = useMemo(() => {
    const set = new Set(list.map((i) => i.metadata.issueType).filter(Boolean));
    return Array.from(set).sort();
  }, [list]);

  const filteredList = useMemo(() => {
    let result = list;
    if (issueTypeFilter) {
      result = result.filter((i) => i.metadata.issueType === issueTypeFilter);
    }
    return sortItems(result, sort);
  }, [list, issueTypeFilter, sort]);

  return (
    <div className="min-h-screen flex flex-col bg-linear-to-b from-zinc-50 to-white dark:from-zinc-950 dark:to-zinc-900">
      <header className="w-full border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100"
              aria-label="Back to home"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
            </Link>
            <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              PS2 Analysis Results
            </h1>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-6">
        {loading && (
          <div className="flex items-center justify-center py-16">
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Loading analysis results…
            </p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-sm text-red-800 dark:text-red-200">
            {error}
          </div>
        )}

        {!loading && !error && list.length === 0 && (
          <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-8 text-center">
            <p className="text-zinc-500 dark:text-zinc-400">
              No analysis results found. Ensure data-normalization output is
              available.
            </p>
          </div>
        )}

        {!loading && !error && list.length > 0 && (
          <>
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                <span>Sort:</span>
                <select
                  value={sort}
                  onChange={(e) =>
                    setSort(e.target.value as SortOption)
                  }
                  className="rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-3 py-1.5 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="satisfaction-low">Satisfaction: Low first</option>
                  <option value="satisfaction-high">
                    Satisfaction: High first
                  </option>
                  <option value="date-newest">Date: Newest first</option>
                  <option value="date-oldest">Date: Oldest first</option>
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                <span>Issue type:</span>
                <select
                  value={issueTypeFilter}
                  onChange={(e) => setIssueTypeFilter(e.target.value)}
                  className="rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-3 py-1.5 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">All</option>
                  {issueTypes.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <span className="text-sm text-zinc-500 dark:text-zinc-400">
                {filteredList.length} result{filteredList.length !== 1 ? "s" : ""}
              </span>
            </div>

            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredList.map((item) => {
                const ratio = satisfactionRatio(item);
                const { score, maxScore } = item.partnerSatisfactionScore;
                return (
                  <li key={item.id}>
                    <Link
                      href={`/ps2-analysis-results/${encodeURIComponent(item.id)}`}
                      className="block rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 shadow-sm hover:border-emerald-500/50 dark:hover:border-emerald-500/50 hover:shadow-md transition-all"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <h2 className="font-medium text-zinc-900 dark:text-zinc-100 line-clamp-2">
                          {item.metadata.name}
                        </h2>
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                            ratio < 0.4
                              ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                              : ratio < 0.7
                                ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
                                : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                          }`}
                        >
                          {score}/{maxScore}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-1">
                        {item.metadata.date}
                      </p>
                      <p className="text-sm text-zinc-600 dark:text-zinc-300 line-clamp-2">
                        {item.metadata.issueType}
                      </p>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </main>

      <footer className="w-full border-t border-zinc-200 dark:border-zinc-800 py-4">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-center">
          <p className="text-xs text-zinc-400 dark:text-zinc-500">
            Built for Hackathon 2026
          </p>
        </div>
      </footer>
    </div>
  );
}
