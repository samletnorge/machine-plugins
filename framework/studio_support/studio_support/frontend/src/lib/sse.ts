export function createEventStream(url: string): EventSource {
  return new EventSource(url);
}
