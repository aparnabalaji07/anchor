import households from "../mockData.json";

export default function CallListPage() {
  return (
    <div>
      <h1>Call List</h1>
      <p>{households.length} households loaded</p>
    </div>
  );
}
