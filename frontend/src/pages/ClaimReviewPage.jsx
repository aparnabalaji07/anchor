import { useParams } from "react-router-dom";

export default function ClaimReviewPage() {
  const { id } = useParams();
  return <h1>Claim Review for Household {id}</h1>;
}
