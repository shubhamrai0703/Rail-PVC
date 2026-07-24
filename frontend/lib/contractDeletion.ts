import type { QueryClient } from "@tanstack/react-query";

type ContractListEntry = {
  id: string;
};

export async function completeContractDeletion(
  queryClient: QueryClient,
  contractId: string,
  navigate: () => void,
): Promise<void> {
  queryClient.setQueryData<ContractListEntry[]>(
    ["contracts"],
    (contracts) => contracts?.filter((contract) => contract.id !== contractId),
  );
  queryClient.removeQueries({
    queryKey: ["contract", contractId],
    exact: true,
  });
  await queryClient.invalidateQueries({
    queryKey: ["contracts"],
    exact: true,
  });
  navigate();
}
