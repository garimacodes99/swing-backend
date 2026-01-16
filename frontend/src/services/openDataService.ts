export async function fetchOpenSnapshot() {
  const res = await fetch("/data/open/swing_open_latest.json");

  if (!res.ok) {
    throw new Error("Failed to fetch open snapshot");
  }

  return res.json();
}
