import { useState } from "react";
import type { Household } from "../api";
import { api } from "../api";
import { useLoad } from "../ui";
import { AccountsSection } from "./manage/AccountsSection";
import { BrokersSection } from "./manage/BrokersSection";
import { CategoriesSection } from "./manage/CategoriesSection";
import { DangerZone, HouseholdSection } from "./manage/HouseholdSection";
import { InstrumentsSection } from "./manage/InstrumentsSection";
import { MembersSection } from "./manage/MembersSection";

export function ManagePage({ household, onHouseholdsChanged, onHouseholdDeleted }: {
  household: Household; onHouseholdsChanged: () => void; onHouseholdDeleted: (id: number) => void;
}) {
  const hid = household.id;
  const members = useLoad(() => api.members(hid), [hid]);
  const [accountsVersion, setAccountsVersion] = useState(0);   // 증권사 연결이 계좌를 만들면 계좌 목록을 새로
  return (
    <div className="grid">
      <HouseholdSection household={household} onChanged={onHouseholdsChanged} />
      <MembersSection hid={hid} members={members.data ?? []} reload={members.reload} error={members.error} />
      <AccountsSection key={accountsVersion} hid={hid} members={members.data ?? []} />
      <BrokersSection hid={hid} members={members.data ?? []} onAccountsChanged={() => setAccountsVersion((v) => v + 1)} />
      <InstrumentsSection hid={hid} />
      <CategoriesSection hid={hid} />
      <DangerZone household={household} onDeleted={() => onHouseholdDeleted(hid)} />
    </div>
  );
}
