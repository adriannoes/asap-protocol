const passwords = new Map<string, string>();

function key(service: string, account: string): string {
  return `${service}::${account}`;
}

export default {
  async getPassword(service: string, account: string): Promise<string | null> {
    return passwords.get(key(service, account)) ?? null;
  },
  async setPassword(service: string, account: string, password: string): Promise<void> {
    passwords.set(key(service, account), password);
  },
  async deletePassword(service: string, account: string): Promise<boolean> {
    return passwords.delete(key(service, account));
  },
};
