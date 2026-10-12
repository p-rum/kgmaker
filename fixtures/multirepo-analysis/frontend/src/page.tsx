export async function ExposurePage() {
  const response = await fetch('/api/exposure');
  const data = await response.json();
  return <span data-testid="decline">{data.decline}</span>;
}
