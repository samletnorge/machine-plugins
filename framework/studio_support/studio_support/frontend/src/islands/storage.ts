import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('storage-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'storage',
      title: 'Storage',
      endpoint: target.dataset.endpoint ?? '/_studio/api/storage/files'
    }
  });
}
