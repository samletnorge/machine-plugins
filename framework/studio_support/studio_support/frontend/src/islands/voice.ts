import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('voice-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'voice',
      title: 'Voice',
      endpoint: target.dataset.endpoint ?? '/_studio/api/voice/voices'
    }
  });
}
