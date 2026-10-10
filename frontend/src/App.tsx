import { useEffect, useState } from 'react';
import './index.css';
import Landing from './Landing';
import Dashboard from './Dashboard';

function useHashRoute(): string {
  const get = () => window.location.hash.replace(/^#\/?/, '');
  const [route, setRoute] = useState(get);
  useEffect(() => {
    const onChange = () => setRoute(get());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

export default function App() {
  const route = useHashRoute();
  if (route === 'console') return <Dashboard />;
  return <Landing />;
}
