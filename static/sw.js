/* 晨鐘 Service Worker
   原則：外殼可離線（cache-first），市場資料絕不快取（/api 一律走網路）——
   寧可顯示錯誤，也不給你舊行情。 */
"use strict";

const CACHE = "morningbell-v2";
const SHELL = [
  "/",
  "/static/app.css?v=2",
  "/static/app.js?v=2",
  "/static/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // 市場資料永遠走網路，失敗就讓前端顯示錯誤
  if (url.pathname.startsWith("/api/")) return;

  // 靜態外殼：先給快取（快），背景更新（新）
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const refresh = fetch(event.request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || refresh;
    })
  );
});
