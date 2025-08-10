// src/lib/api.js
import { API_BASE } from "../config";

const DEFAULT_TIMEOUT = 15000; // ms

function timeoutFetch(resource, options = {}, timeout = DEFAULT_TIMEOUT) {
  return Promise.race([
    fetch(resource, options),
    new Promise((_, reject) => setTimeout(() => reject(new Error("Timeout")), timeout))
  ]);
}

export function get(path, opts = {}) {
  const url = `${API_BASE}${path}`;
  const headers = Object.assign({ "Accept": "application/json" }, opts.headers || {});
  if (opts.token) headers["Authorization"] = `Bearer ${opts.token}`;
  return timeoutFetch(url, { method: "GET", headers }).then(res => {
    if (!res.ok) throw res;
    return res.json();
  });
}

export function post(path, body = {}, opts = {}) {
  const url = `${API_BASE}${path}`;
  const headers = Object.assign({ "Accept": "application/json", "Content-Type": "application/json" }, opts.headers || {});
  if (opts.token) headers["Authorization"] = `Bearer ${opts.token}`;
  return timeoutFetch(url, { method: "POST", headers, body: JSON.stringify(body) }).then(res => {
    if (!res.ok) throw res;
    return res.json().catch(() => ({}));
  });
}

export function del(path, opts = {}) {
  const url = `${API_BASE}${path}`;
  const headers = Object.assign({ "Accept": "application/json" }, opts.headers || {});
  if (opts.token) headers["Authorization"] = `Bearer ${opts.token}`;
  return timeoutFetch(url, { method: "DELETE", headers }).then(res => {
    if (!res.ok) throw res;
    return res.json().catch(() => ({}));
  });
}