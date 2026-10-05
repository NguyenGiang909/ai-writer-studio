"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { API } from "../lib/api";
import { t } from "../lib/i18n";
import { getLangClient } from "../lib/use-lang";

function toast(msg: string) {
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

export default function AppBehaviors({ projectId }: { projectId: string }) {
  const router = useRouter();

  useEffect(() => {
    let dragged: HTMLElement | null = null;

    async function persistOrder(listEl: Element) {
      const rows = [...listEl.querySelectorAll<HTMLElement>(".chapter-row")];
      await Promise.all(
        rows.map((r, i) =>
          fetch(`${API}/api/v1/projects/${projectId}/chapters/${r.dataset.chapterId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ order_index: i + 1 }),
          })
        )
      );
      router.refresh();
    }

    function onClick(e: MouseEvent) {
      const el = e.target as HTMLElement;

      const modeBtn = el.closest<HTMLElement>(".mode button");
      if (modeBtn) {
        modeBtn.parentElement?.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        modeBtn.classList.add("active");
        toast(`${modeBtn.textContent} mode`);
        return;
      }

      if (el.closest(".menu-toggle")) {
        document.querySelector(".left")?.classList.toggle("open");
        return;
      }
      if (el.closest(".ai-toggle")) {
        document.querySelector(".right")?.classList.toggle("open");
        return;
      }

      // click chapter row (not on a scene link / form) → open first scene
      const row = el.closest<HTMLElement>(".chapter-row");
      if (row && !el.closest(".scene-row") && !el.closest(".postform") && !el.closest("a") && !el.closest(".chapter-toggle")) {
        const first = row.dataset.firstScene;
        if (first) router.push(`/projects/${projectId}?scene=${first}`);
        else {
          window.dispatchEvent(new CustomEvent("writer:toggle-chapter", { detail: row.dataset.chapterId }));
          toast(t(getLangClient(), "Chương chưa có cảnh — thêm cảnh để viết"));
        }
        return;
      }

      // nav clicked on mobile → close drawer
      if (el.closest(".nav-item") && window.innerWidth < 760) {
        document.querySelector(".left")?.classList.remove("open");
      }
    }

    function onKeydown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        document.querySelector(".left")?.classList.remove("open");
        document.querySelector(".right")?.classList.remove("open");
      }
    }

    async function persistSort(listEl: HTMLElement, moved: HTMLElement) {
      const kind = listEl.dataset.sortList;
      if (!kind) return;
      const base = `${API}/api/v1/projects/${projectId}/${kind}`;
      const newBucket = (moved.parentElement as HTMLElement)?.dataset?.bucket;
      const oldBucket = moved.dataset.bucket;
      const id = moved.dataset.dragId;
      if (id && newBucket !== undefined && newBucket !== oldBucket) {
        moved.dataset.bucket = newBucket;
        await fetch(`${base}/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ importance: Number(newBucket) }),
        });
      }
      const ids = [...listEl.querySelectorAll<HTMLElement>(".sort-row")].map((r) => r.dataset.dragId);
      await fetch(`${base}/reorder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids }),
      });
      router.refresh();
    }

    function onDragStart(e: DragEvent) {
      const row = (e.target as HTMLElement).closest<HTMLElement>(".chapter-row, .sort-row");
      if (!row) return;
      dragged = row;
      row.dataset.bucket = (row.parentElement as HTMLElement)?.dataset?.bucket ?? "";
      row.classList.add("dragging");
    }
    function onDragEnd() {
      dragged?.classList.remove("dragging");
      document.querySelectorAll(".chapter-row.drag-over, .sort-row.drag-over").forEach((x) => x.classList.remove("drag-over"));
      dragged = null;
    }
    function onDragOver(e: DragEvent) {
      if (!dragged) return;
      const tgt = e.target as HTMLElement;
      if (dragged.classList.contains("chapter-row")) {
        const row = tgt.closest<HTMLElement>(".chapter-row");
        if (!row || dragged === row || row.parentElement !== dragged.parentElement) return;
        e.preventDefault();
        row.classList.add("drag-over");
        return;
      }
      const list = tgt.closest<HTMLElement>("[data-sort-list]");
      if (!list || list !== dragged.closest("[data-sort-list]")) return;
      e.preventDefault();
      const row = tgt.closest<HTMLElement>(".sort-row");
      if (row && row !== dragged) row.classList.add("drag-over");
    }
    function onDragLeave(e: DragEvent) {
      (e.target as HTMLElement).closest(".chapter-row, .sort-row")?.classList.remove("drag-over");
    }
    function onDrop(e: DragEvent) {
      if (!dragged) return;
      const tgt = e.target as HTMLElement;
      if (dragged.classList.contains("chapter-row")) {
        const row = tgt.closest<HTMLElement>(".chapter-row");
        if (!row || dragged === row || row.parentElement !== dragged.parentElement) return;
        e.preventDefault();
        row.classList.remove("drag-over");
        const box = row.getBoundingClientRect();
        row.parentElement!.insertBefore(dragged, e.clientY < box.top + box.height / 2 ? row : row.nextSibling);
        toast(t(getLangClient(), "Đã sắp xếp lại chương"));
        persistOrder(row.parentElement!);
        return;
      }
      const list = tgt.closest<HTMLElement>("[data-sort-list]");
      if (!list || list !== dragged.closest("[data-sort-list]")) return;
      e.preventDefault();
      const row = tgt.closest<HTMLElement>(".sort-row");
      if (row && row !== dragged) {
        const box = row.getBoundingClientRect();
        row.parentElement!.insertBefore(dragged, e.clientY < box.top + box.height / 2 ? row : row.nextSibling);
      } else if (!row) {
        const bucket = tgt.closest<HTMLElement>("[data-bucket]");
        if (!bucket) return;
        bucket.appendChild(dragged);
      }
      toast(t(getLangClient(), "Đã sắp xếp lại"));
      persistSort(list as HTMLElement, dragged);
    }

    document.addEventListener("click", onClick);
    document.addEventListener("keydown", onKeydown);
    document.addEventListener("dragstart", onDragStart);
    document.addEventListener("dragend", onDragEnd);
    document.addEventListener("dragover", onDragOver);
    document.addEventListener("dragleave", onDragLeave);
    document.addEventListener("drop", onDrop);
    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("keydown", onKeydown);
      document.removeEventListener("dragstart", onDragStart);
      document.removeEventListener("dragend", onDragEnd);
      document.removeEventListener("dragover", onDragOver);
      document.removeEventListener("dragleave", onDragLeave);
      document.removeEventListener("drop", onDrop);
    };
  }, [projectId, router]);

  return null;
}
