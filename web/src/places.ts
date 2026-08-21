/**
 * Somewhere to search from.
 *
 * The registry's distance filter needs a latitude and longitude, and asking a
 * person to type coordinates is not a product. Turning "Portland, Oregon" into
 * coordinates is called geocoding, it needs a service we have not chosen, and it
 * is its own task — `D-4` in the backlog. Until then this short list of cities
 * makes the query path real and demonstrable without pretending to be finished.
 *
 * "Anywhere" is not a placeholder: searching with no coordinates is a legitimate
 * query. It returns trials without any distance claim attached, which is better
 * than a distance we would have to invent.
 *
 * **D-4 update:** you can now type a place name and the server looks it up. This
 * list survives as the fallback for when that lookup is down, and as the quick
 * path for the demo. A place found by searching becomes a `Place` exactly like
 * these, so nothing downstream knows the difference.
 */

export interface Place {
  name: string;
  latitude: number | null;
  longitude: number | null;
}

export const PLACES: Place[] = [
  { name: "Anywhere (no distance shown)", latitude: null, longitude: null },
  { name: "Portland, Oregon", latitude: 45.5152, longitude: -122.6784 },
  { name: "Boston, Massachusetts", latitude: 42.3601, longitude: -71.0589 },
  { name: "Chicago, Illinois", latitude: 41.8781, longitude: -87.6298 },
  { name: "Houston, Texas", latitude: 29.7604, longitude: -95.3698 },
  { name: "Los Angeles, California", latitude: 34.0522, longitude: -118.2437 },
  { name: "New York, New York", latitude: 40.7128, longitude: -74.006 },
];

/** Where a searched-for place sits in the list: appended, and selected. */
export function withFoundPlace(places: Place[], found: Place): { places: Place[]; index: number } {
  const existing = places.findIndex((p) => p.name === found.name);
  if (existing >= 0) return { places, index: existing };
  return { places: [...places, found], index: places.length };
}
