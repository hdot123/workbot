const REQUEST_TIMEOUT = 15_000;

export class ConnectClient {
  private host: string;
  private apiKey: string;
  private callCount = 0;

  constructor(host: string, apiKey: string) {
    this.host = host.replace(/\/+$/, '');
    this.apiKey = apiKey;
  }

  get callCountSnapshot(): number {
    return this.callCount;
  }

  resetCallCount(): void {
    this.callCount = 0;
  }

  private async request(path: string): Promise<unknown> {
    const url = `${this.host}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

    this.callCount++;
    try {
      const res = await fetch(url, {
        method: 'GET',
        headers: {
          apikey: this.apiKey,
          Accept: 'application/json',
        },
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`Connect API ${res.status}: ${body.slice(0, 200)}`);
      }
      return await res.json();
    } catch (err) {
      clearTimeout(timer);
      if ((err as Error).name === 'AbortError') {
        throw new Error(`Connect API timeout after ${REQUEST_TIMEOUT}ms for ${path}`);
      }
      throw err;
    }
  }

  async listVaults(): Promise<unknown[]> {
    return (await this.request('/v1/vaults')) as unknown[];
  }

  async listItems(vaultId: string): Promise<unknown[]> {
    return (await this.request(`/v1/vaults/${encodeURIComponent(vaultId)}/items`)) as unknown[];
  }

  async getItem(vaultId: string, itemId: string): Promise<unknown> {
    return await this.request(`/v1/vaults/${encodeURIComponent(vaultId)}/items/${encodeURIComponent(itemId)}`);
  }

  async searchItems(vaultId: string, query: string): Promise<unknown[]> {
    const filter = `title eq "${query}"`;
    return (await this.request(`/v1/vaults/${encodeURIComponent(vaultId)}/items?filter=${encodeURIComponent(filter)}`)) as unknown[];
  }
}
