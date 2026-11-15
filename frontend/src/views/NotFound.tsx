import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <section className="page">
      <p className="eyebrow">404</p>
      <h1>Page not found</h1>
      <p>That address is not part of ILKA.</p>
      <Link className="button" to="/">
        Back to dashboard
      </Link>
    </section>
  );
}
