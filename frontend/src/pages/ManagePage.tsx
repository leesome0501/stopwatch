import type { Household } from "../api";
import { api } from "../api";
import { useLoad } from "../ui";
import { AccountsSection } from "./manage/AccountsSection";
import { CategoriesSection } from "./manage/CategoriesSection";
import { DangerZone, HouseholdSection } from "./manage/HouseholdSection";
import { InstrumentsSection } from "./manage/InstrumentsSection";
import { MembersSection } from "./manage/MembersSection";

export function ManagePage({ household, onHouseholdsChanged, onHouseholdDeleted }: {
  household: Household; onHouseholdsChanged: () => void; onHouseholdDeleted: (id: number) => void;
}) {
  const hid = household.id;
  const members = useLoad(() => api.members(hid), [hid]);
  return (
    <div className="grid">
      <HouseholdSection household={household} onChanged={onHouseholdsChanged} />
      <MembersSection hid={hid} members={members.data ?? []} reload={members.reload} error={members.error} />
      <AccountsSection hid={hid} members={members.data ?? []} />
      <InstrumentsSection hid={hid} />
      <CategoriesSection hid={hid} />
      <DangerZone household={household} onDeleted={() => onHouseholdDeleted(hid)} />
    </div>
  );
}
