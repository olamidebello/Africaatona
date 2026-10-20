'use strict';
const menu = document.querySelector('.menu');
const navigation = document.getElementById('navigation');
menu.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true';
  menu.setAttribute('aria-expanded', String(open));
  navigation.classList.toggle('open', open);
});
navigation.addEventListener('click', event => {
  if (event.target.closest('a')) {
    navigation.classList.remove('open');
    menu.setAttribute('aria-expanded', 'false');
  }
});
document.getElementById('year').textContent = new Date().getFullYear();
fetch('/api/capabilities').then(response => {
  if (!response.ok) throw new Error('Capabilities unavailable');
  return response.json();
}).then(capabilities => {
  const link = document.getElementById('apk-download');
  const status = document.getElementById('download-status');
  if (capabilities.apk) {
    link.href = '/downloads/africa-atona.apk';
    link.setAttribute('download', 'africa-atona.apk');
    status.textContent = 'Android development beta · Download the APK to install on your device.';
  } else {
    link.href = '/map.html';
    link.textContent = 'Open Africa Atona ↗';
    status.textContent = 'Android download is not available yet. Use the web map or add it to your home screen.';
  }
}).catch(() => {
  document.getElementById('apk-download').href = '/map.html';
  document.getElementById('apk-download').textContent = 'Open Africa Atona ↗';
  document.getElementById('download-status').textContent = 'Use the web map. Android download availability could not be checked.';
});
