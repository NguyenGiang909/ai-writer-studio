"use client";
import { useRouter } from "next/navigation";

export default function ChapterSelect({
  options,
  current,
  base,
}: {
  options: { value: string; label: string }[];
  current: string;
  base: string;
}) {
  const router = useRouter();
  return (
    <select
      value={current}
      onChange={(e) => router.push(`${base}?chapter=${e.target.value}`)}
      style={{ maxWidth: 280 }}
      aria-label="Chọn chương"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}
