import { useParams } from "react-router-dom";

export default function HouseholdPage() {
  const { id } = useParams();
  return <h1>Household {id}</h1>;
}
