import { NavLink } from "react-router-dom";

export default function NavBar() {
  return (
    <nav className="nav">
      <strong>[Project Name]</strong>
      <NavLink to="/">Call List</NavLink>
      <NavLink to="/map">Map</NavLink>
    </nav>
  );
}
