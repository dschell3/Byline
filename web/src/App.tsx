import { Link } from 'react-router';

export default function App() {
  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-page-title">Byline</h1>
      <p className="mt-2">
        A record of real work. The app is being built. See the{' '}
        <Link className="text-primary underline" to="/tokens">
          design tokens
        </Link>
        .
      </p>
    </main>
  );
}