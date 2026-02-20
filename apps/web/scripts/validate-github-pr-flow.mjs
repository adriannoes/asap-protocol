#!/usr/bin/env node
/** Pre-M2: test GitHub PR flow. Run: GITHUB_TOKEN=<pat> node apps/web/scripts/validate-github-pr-flow.mjs */
import { Octokit } from 'octokit';

const token = process.env.GITHUB_TOKEN;
if (!token) {
  console.error('Set GITHUB_TOKEN (Personal Access Token with repo scope)');
  process.exit(1);
}

const OWNER = process.env.GITHUB_REGISTRY_OWNER || 'asap-protocol';
const REPO = process.env.GITHUB_REGISTRY_REPO || 'registry';
const DRY_RUN = process.env.DRY_RUN === '1';

const octokit = new Octokit({ auth: token });

async function main() {
  try {
    // 1. Check repo exists
    const { data: repo } = await octokit.rest.repos.get({ owner: OWNER, repo: REPO });
    console.log('✓ Repo exists:', repo.full_name);

    const defaultBranch = repo.default_branch || 'main';
    console.log('✓ Default branch:', defaultBranch);

    if (DRY_RUN) {
      console.log('\n✅ Dry run: repo check passed. Run without DRY_RUN=1 to test full flow.');
      return;
    }

    // 2. Get current registry.json (if exists)
    let currentContent = '[]';
    try {
      const { data } = await octokit.rest.repos.getContent({
        owner: OWNER,
        repo: REPO,
        path: 'registry.json',
      });
      if ('content' in data && data.content) {
        currentContent = Buffer.from(data.content, 'base64').toString();
      }
    } catch (e) {
      if (e.status === 404) {
        console.log('⚠ registry.json not found (will create)');
      } else {
        throw e;
      }
    }

    // 3. Fork
    const { data: fork } = await octokit.rest.repos.createFork({ owner: OWNER, repo: REPO });
    console.log('✓ Fork created:', fork.full_name);

    // 4. Create branch on fork
    const branchName = 'register/test-agent-' + Date.now();
    const { data: ref } = await octokit.rest.git.getRef({
      owner: fork.owner.login,
      repo: fork.name,
      ref: 'heads/' + defaultBranch,
    });
    await octokit.rest.git.createRef({
      owner: fork.owner.login,
      repo: fork.name,
      ref: 'refs/heads/' + branchName,
      sha: ref.object.sha,
    });
    console.log('✓ Branch created:', branchName);

    let fileSha = null;
    try {
      const { data: file } = await octokit.rest.repos.getContent({
        owner: fork.owner.login,
        repo: fork.name,
        path: 'registry.json',
        ref: branchName,
      });
      if ('sha' in file) fileSha = file.sha;
    } catch (e) {
      if (e.status !== 404) throw e;
    }

    const newEntry = {
      id: 'urn:asap:test-agent-' + Date.now(),
      name: 'test-agent',
      description: 'Pre-M2 validation test',
      endpoints: { http: 'https://example.com/asap' },
      skills: ['test'],
    };
    const registry = JSON.parse(currentContent);
    if (!Array.isArray(registry)) {
      throw new Error('registry.json must be an array');
    }
    registry.push(newEntry);
    const newContent = JSON.stringify(registry, null, 2);

    await octokit.rest.repos.createOrUpdateFileContents({
      owner: fork.owner.login,
      repo: fork.name,
      path: 'registry.json',
      message: 'chore: pre-M2 validation test',
      content: Buffer.from(newContent).toString('base64'),
      branch: branchName,
      ...(fileSha && { sha: fileSha }),
    });
    console.log('✓ File updated');

    // 6. Create PR
    const { data: pr } = await octokit.rest.pulls.create({
      owner: OWNER,
      repo: REPO,
      title: 'Register Agent: test-agent (Pre-M2 validation)',
      head: fork.owner.login + ':' + branchName,
      base: defaultBranch,
      body:
        'Automated registration via Marketplace. **Pre-M2 validation test** — safe to close.',
    });
    console.log('✓ PR created:', pr.html_url);
    console.log('\n✅ All steps passed. GitHub flow is ready for M2.');
  } catch (err) {
    console.error('❌ Error:', err.message);
    if (err.response) {
      console.error('   Status:', err.response.status);
      console.error('   Data:', JSON.stringify(err.response.data, null, 2));
    }
    process.exit(1);
  }
}

main();
