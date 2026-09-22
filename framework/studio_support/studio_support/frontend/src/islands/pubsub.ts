import { mount } from 'svelte';
import DomainPanel from '../components/DomainPanel.svelte';

const target = document.getElementById('pubsub-island');

if (target) {
  mount(DomainPanel, {
    target,
    props: {
      domain: 'pubsub',
      title: 'Pub/Sub',
      endpoint: target.dataset.endpoint ?? '/_studio/api/pubsub/events'
    }
  });
}
