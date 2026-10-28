// Mobile menu: <details> already opens and closes without JS. This only closes it after
// choosing a link (same-page anchors don't reload), on Escape, or when tapping outside.

const menu = document.querySelector<HTMLDetailsElement>('details.menu');

if (menu) {
  const close = () => {
    menu.open = false;
  };

  menu.addEventListener('click', (event) => {
    if ((event.target as Element).closest('a')) close();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu.open) {
      close();
      menu.querySelector('summary')?.focus();
    }
  });

  document.addEventListener('click', (event) => {
    if (menu.open && !menu.contains(event.target as Node)) close();
  });
}

export {};
