import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { completeContractDeletion } from "./contractDeletion";

describe("completeContractDeletion", () => {
  it("updates and invalidates the list and clears detail before navigation", async () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(["contracts"], [
      { id: "contract-1", tender_number: "T-1" },
      { id: "contract-2", tender_number: "T-2" },
    ]);
    queryClient.setQueryData(["contract", "contract-1"], {
      id: "contract-1",
      tender_number: "T-1",
    });

    const navigate = vi.fn(() => {
      expect(queryClient.getQueryData(["contracts"])).toEqual([
        { id: "contract-2", tender_number: "T-2" },
      ]);
      expect(queryClient.getQueryData(["contract", "contract-1"])).toBeUndefined();
      expect(
        queryClient.getQueryState(["contracts"])?.isInvalidated,
      ).toBe(true);
    });

    await completeContractDeletion(queryClient, "contract-1", navigate);

    expect(navigate).toHaveBeenCalledOnce();
  });
});
