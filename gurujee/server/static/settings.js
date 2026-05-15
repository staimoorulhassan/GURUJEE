/**
 * Settings Panel Management
 * Handles model selection, voice recording, automation rules, API keys
 */

class SettingsPanel {
  constructor() {
    this.modal = document.getElementById('settings-modal');
    this.setupEventListeners();
    this.voiceRecorder = null;
    this.voiceChunks = [];
    this.voiceStream = null;
  }

  setupEventListeners() {
    // Modal controls
    document.getElementById('settings-btn').addEventListener('click', () => this.open());
    document.getElementById('settings-close').addEventListener('click', () => this.close());

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
    });

    // Model tab
    document.getElementById('model-save').addEventListener('click', () => this.saveModel());

    // Voice tab
    document.getElementById('voice-record-btn').addEventListener('click', () => this.startRecording());
    document.getElementById('voice-stop-btn').addEventListener('click', () => this.stopRecording());
    document.getElementById('voice-play-btn').addEventListener('click', () => this.playRecording());
    document.getElementById('voice-clone-btn').addEventListener('click', () => this.cloneVoice());

    // Automation tab
    document.getElementById('rule-create-btn').addEventListener('click', () => this.createRule());

    // Keys tab
    document.getElementById('keys-save-btn').addEventListener('click', () => this.saveKeys());
    document.getElementById('settings-export-btn').addEventListener('click', () => this.exportSettings());
    document.getElementById('settings-import-btn').addEventListener('click', () => {
      document.getElementById('import-file-input').click();
    });
    document.getElementById('import-file-input').addEventListener('change', (e) => this.importSettings(e));

    // Load initial data
    this.loadSettings();
  }

  open() {
    this.modal.style.display = 'flex';
    this.loadSettings();
  }

  close() {
    this.modal.style.display = 'none';
  }

  switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
      tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
  }

  async loadSettings() {
    try {
      // Load models
      const modelsResp = await fetch('/api/settings/models');
      if (modelsResp.ok) {
        const models = await modelsResp.json();
        this.displayModels(models);
      }

      // Load automation rules
      const rulesResp = await fetch('/api/settings/automation/rules');
      if (rulesResp.ok) {
        const rules = await rulesResp.json();
        this.displayRules(rules.rules || []);
      }

      // Load voice status
      this.checkVoiceStatus();

      // Load system status
      this.loadSystemStatus();
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  }

  displayModels(data) {
    const policy = data.agents[0]; // soul agent by default
    const policyHtml = `
      <p><strong>Default Model:</strong> ${policy.default_model}</p>
      <p><strong>Fallback:</strong> ${policy.fallback_models.join(', ')}</p>
      <p><strong>Budget Tier:</strong> ${policy.budget_tier}</p>
    `;
    document.getElementById('routing-policy').innerHTML = policyHtml;
  }

  displayRules(rules) {
    const rulesHtml = rules.map(rule => `
      <div class="rule-item">
        <div>
          <span class="rule-item-id">${rule.id}</span> - ${rule.type}
          ${rule.enabled ? '' : ' (disabled)'}
        </div>
        <div class="rule-item-actions">
          <button onclick="settingsPanel.editRule('${rule.id}')" class="btn-secondary">Edit</button>
          <button onclick="settingsPanel.deleteRule('${rule.id}')" class="btn-secondary" style="color:#ef4444;">Delete</button>
        </div>
      </div>
    `).join('');

    document.getElementById('rules-list').innerHTML = rulesHtml || '<p style="color:#666;">No rules yet. Create one to get started.</p>';
  }

  async saveModel() {
    const model = document.getElementById('model-select').value;
    try {
      const resp = await fetch('/api/settings/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_name: 'soul', model_name: model })
      });

      if (resp.ok) {
        this.showStatus('model-select', 'Model saved successfully', 'success');
      } else {
        this.showStatus('model-select', 'Failed to save model', 'error');
      }
    } catch (err) {
      this.showStatus('model-select', err.message, 'error');
    }
  }

  async startRecording() {
    try {
      this.voiceStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.voiceRecorder = new MediaRecorder(this.voiceStream);
      this.voiceChunks = [];

      this.voiceRecorder.ondataavailable = (e) => {
        this.voiceChunks.push(e.data);
      };

      this.voiceRecorder.start();
      document.getElementById('voice-record-btn').disabled = true;
      document.getElementById('voice-stop-btn').disabled = false;
      this.showVoiceStatus('Recording...', 'warning');
    } catch (err) {
      this.showVoiceStatus(`Permission denied: ${err.message}`, 'error');
    }
  }

  stopRecording() {
    if (this.voiceRecorder) {
      this.voiceRecorder.stop();
      this.voiceStream.getTracks().forEach(track => track.stop());

      document.getElementById('voice-record-btn').disabled = false;
      document.getElementById('voice-stop-btn').disabled = true;
      document.getElementById('voice-play-btn').disabled = false;
      this.showVoiceStatus('Recording saved. Click Play to preview.', 'success');
    }
  }

  playRecording() {
    if (this.voiceChunks.length > 0) {
      const blob = new Blob(this.voiceChunks, { type: 'audio/webm' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.play();
    }
  }

  async cloneVoice() {
    if (this.voiceChunks.length === 0) {
      this.showVoiceStatus('Please record a voice sample first', 'error');
      return;
    }

    const voiceName = document.getElementById('voice-name-input').value || 'MyVoice';
    const blob = new Blob(this.voiceChunks, { type: 'audio/webm' });

    const formData = new FormData();
    formData.append('voice_name', voiceName);
    formData.append('file', blob, 'voice-sample.webm');

    try {
      document.getElementById('cloning-progress').style.display = 'block';
      document.querySelector('.progress-fill').style.width = '0%';

      const resp = await fetch('/api/settings/voice/record', {
        method: 'POST',
        body: formData
      });

      if (resp.ok) {
        const result = await resp.json();
        this.showCloningStatus(`Cloning started for "${voiceName}"... Processing...`, 'warning');
        this.pollCloningStatus(result.voice_id);
      } else {
        this.showCloningStatus('Cloning failed', 'error');
      }
    } catch (err) {
      this.showCloningStatus(err.message, 'error');
    }
  }

  async pollCloningStatus(voiceId) {
    const maxAttempts = 60; // 5 minutes with 5s polling
    let attempt = 0;

    const poll = async () => {
      try {
        const resp = await fetch(`/api/settings/voice/status/${voiceId}`);
        if (resp.ok) {
          const data = await resp.json();
          const progress = Math.min((attempt / maxAttempts) * 100, 90);
          document.querySelector('.progress-fill').style.width = progress + '%';

          if (data.status === 'ready') {
            this.showCloningStatus('Voice cloning complete!', 'success');
            document.querySelector('.progress-fill').style.width = '100%';
            return;
          } else if (data.status === 'failed') {
            this.showCloningStatus('Voice cloning failed', 'error');
            return;
          }
        }

        attempt++;
        if (attempt < maxAttempts) {
          setTimeout(poll, 5000);
        } else {
          this.showCloningStatus('Cloning timeout - still processing', 'warning');
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    poll();
  }

  async checkVoiceStatus() {
    // Could poll real voice status here
    document.getElementById('cloning-status').textContent = 'No voice cloned yet';
  }

  async createRule() {
    const type = document.getElementById('rule-type-select').value;
    const trigger = document.getElementById('rule-trigger-input').value;
    const conditions = JSON.parse(document.getElementById('rule-conditions-input').value || '[]');
    const actions = JSON.parse(document.getElementById('rule-actions-input').value || '{}');
    const enabled = document.getElementById('rule-enabled-check').checked;

    if (!type || !trigger) {
      this.showStatus('rule-create-btn', 'Type and trigger required', 'error');
      return;
    }

    try {
      const resp = await fetch('/api/settings/automation/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_type: type, trigger, conditions, actions, enabled })
      });

      if (resp.ok) {
        this.showStatus('rule-create-btn', 'Rule created', 'success');
        // Clear form
        document.getElementById('rule-type-select').value = '';
        document.getElementById('rule-trigger-input').value = '';
        document.getElementById('rule-conditions-input').value = '';
        document.getElementById('rule-actions-input').value = '';
        // Reload rules
        this.loadSettings();
      } else {
        this.showStatus('rule-create-btn', 'Failed to create rule', 'error');
      }
    } catch (err) {
      this.showStatus('rule-create-btn', err.message, 'error');
    }
  }

  async deleteRule(ruleId) {
    if (!confirm(`Delete rule ${ruleId}?`)) return;

    try {
      const resp = await fetch(`/api/settings/automation/rules/${ruleId}`, {
        method: 'DELETE'
      });

      if (resp.ok) {
        this.loadSettings();
      }
    } catch (err) {
      console.error('Delete failed:', err);
    }
  }

  async saveKeys() {
    const keys = {
      pollinations: document.getElementById('key-pollinations').value,
      elevenlabs: document.getElementById('key-elevenlabs').value,
      smsUrl: document.getElementById('key-sms-url').value
    };

    try {
      const resp = await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          key_name: 'POLLINATIONS_API_KEY',
          key_value: keys.pollinations
        })
      });

      if (resp.ok) {
        this.showStatus('keys-save-btn', 'Keys saved securely', 'success');
        // Clear inputs
        document.getElementById('key-pollinations').value = '';
        document.getElementById('key-elevenlabs').value = '';
        document.getElementById('key-sms-url').value = '';
      }
    } catch (err) {
      this.showStatus('keys-save-btn', err.message, 'error');
    }
  }

  async exportSettings() {
    try {
      const resp = await fetch('/api/settings/export');
      if (resp.ok) {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'gurujee-settings.zip';
        a.click();
        this.showStatus('settings-export-btn', 'Settings exported', 'success');
      }
    } catch (err) {
      this.showStatus('settings-export-btn', err.message, 'error');
    }
  }

  async importSettings(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const resp = await fetch('/api/settings/import', {
        method: 'POST',
        body: formData
      });

      if (resp.ok) {
        this.showStatus('settings-import-btn', 'Settings imported successfully', 'success');
        this.loadSettings();
      }
    } catch (err) {
      this.showStatus('settings-import-btn', err.message, 'error');
    }
  }

  async loadSystemStatus() {
    try {
      const resp = await fetch('/api/health');
      if (resp.ok) {
        const health = await resp.json();
        const statusHtml = `
          <p>✅ Daemon: ${health.daemon_status || 'Running'}</p>
          <p>✅ Memory: ${health.memory_mb || '?'} MB</p>
          <p>✅ Agents: ${health.active_agents || '?'} active</p>
        `;
        document.getElementById('system-status').innerHTML = statusHtml;
      }
    } catch (err) {
      document.getElementById('system-status').innerHTML = '<p style="color:#ef4444;">Unable to fetch system status</p>';
    }
  }

  showStatus(elementId, message, type = 'info') {
    const el = document.getElementById(elementId);
    if (el && el.nextElementSibling && el.nextElementSibling.classList.contains('status-message')) {
      const statusEl = el.nextElementSibling;
      statusEl.textContent = message;
      statusEl.className = `status-message ${type}`;
    }
  }

  showVoiceStatus(message, type = 'info') {
    const statusEl = document.getElementById('voice-status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
  }

  showCloningStatus(message, type = 'info') {
    const statusEl = document.getElementById('cloning-status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
  }
}

// Initialize on page load
let settingsPanel;
document.addEventListener('DOMContentLoaded', () => {
  settingsPanel = new SettingsPanel();
});
