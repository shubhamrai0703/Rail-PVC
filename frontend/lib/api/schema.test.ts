import { describe, expectTypeOf, it } from "vitest";

import type { components, operations, paths } from "./schema";

type ContractDelete =
  paths["/api/contracts/{contract_id}"]["delete"];
type ContractDeleteResponses =
  operations["delete_contract_api_contracts__contract_id__delete"]["responses"];
type HasDelete204 = 204 extends keyof ContractDeleteResponses ? true : false;
type HasDelete404 = 404 extends keyof ContractDeleteResponses ? true : false;
type HasDelete422 = 422 extends keyof ContractDeleteResponses ? true : false;
type HasDelete200 = 200 extends keyof ContractDeleteResponses ? true : false;
type CleanupRetry =
  paths["/api/documents/cleanup-pending"]["post"];
type ApiProblemResponse = components["schemas"]["ApiProblemResponse"];
type ApiProblemDetail = components["schemas"]["ApiProblemDetail"];
type OptionalProblemFields = Pick<
  ApiProblemDetail,
  "contract_id" | "blockers" | "entity" | "id" | "field" | "value"
>;
type CleanupResult = components["schemas"]["CleanupResult"];

describe("generated OpenAPI contract", () => {
  it("pins contract DELETE as a 204 operation and exposes cleanup retry", () => {
    expectTypeOf<ContractDelete>().toEqualTypeOf<
      operations["delete_contract_api_contracts__contract_id__delete"]
    >();
    expectTypeOf<HasDelete204>().toEqualTypeOf<true>();
    expectTypeOf<HasDelete404>().toEqualTypeOf<true>();
    expectTypeOf<HasDelete422>().toEqualTypeOf<true>();
    expectTypeOf<HasDelete200>().toEqualTypeOf<false>();
    expectTypeOf<
      ContractDeleteResponses[404]["content"]["application/json"]
    >().toEqualTypeOf<ApiProblemResponse>();
    expectTypeOf<
      ContractDeleteResponses[422]["content"]["application/json"]
    >().toEqualTypeOf<ApiProblemResponse>();
    expectTypeOf<OptionalProblemFields>().toEqualTypeOf<{
      contract_id?: string | null;
      blockers?: string[] | null;
      entity?: string | null;
      id?: string | null;
      field?: string | null;
      value?: unknown | null;
    }>();
    expectTypeOf<CleanupRetry>().toEqualTypeOf<
      operations["retry_pending_document_cleanups_api_documents_cleanup_pending_post"]
    >();
    expectTypeOf<CleanupResult>().toEqualTypeOf<{
      attempted: number;
      succeeded: number;
      failed: number;
      quarantined: number;
      lost_claims: number;
    }>();
  });
});
