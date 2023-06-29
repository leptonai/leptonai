import { Injectable } from "injection-js";
import { EMPTY, map, merge, Observable, of, tap } from "rxjs";
import {
  SelectionChange,
  SelectionModel,
} from "@lepton-libs/cdk/selection-model";

export type DirectoryItem<T> = {
  children: FileEntry<T>[];
} & T;

export type FileEntry<T> = T | DirectoryItem<T>;

@Injectable()
export abstract class FileManagerService<T = Record<string, unknown>> {
  abstract list(file?: T): Observable<T[]>;
  abstract create(file: T, content?: File): Observable<void>;
  abstract remove(file: T): Observable<void>;
}

export interface FileTreeControlOptions<T, K> {
  readonly trackBy: (file: FileEntry<T>) => K;
  readonly isExpandable: (file: FileEntry<T>) => file is DirectoryItem<T>;
  readonly expansionMode?: "single" | "multiple";
  readonly selectionMode?: "single" | "multiple" | "none";
  readonly initData?: readonly FileEntry<T>[];
}

export class FileTreeControl<T, K = FileEntry<T>> {
  // Record the expanded state of the tree nodes.
  private expansionModel: SelectionModel<K>;

  // Record the loading state of the tree nodes.
  private loadingModel = new SelectionModel<K>(true);

  // Record the selected state of the tree nodes.
  private readonly selectionModel: SelectionModel<K> | null = null;

  private data: readonly FileEntry<T>[] | null = this.options.initData || null;

  // The function to use to track changes made to the data.
  readonly trackBy: (file: FileEntry<T>) => K = this.options.trackBy;
  // The function to use to check whether the data node is expandable.
  readonly isExpandable: (file: FileEntry<T>) => file is DirectoryItem<T> =
    this.options.isExpandable;

  constructor(
    public readonly service: FileManagerService<T>,
    private options: FileTreeControlOptions<T, K>
  ) {
    const expansionModel = this.options?.expansionMode || "single";
    const selectionMode = this.options?.selectionMode || "single";
    if (selectionMode === "single") {
      this.selectionModel = new SelectionModel<K>(false);
    } else if (selectionMode === "multiple") {
      this.selectionModel = new SelectionModel<K>(true);
    }
    if (expansionModel === "single") {
      this.expansionModel = new SelectionModel<K>(false);
    } else {
      this.expansionModel = new SelectionModel<K>(true);
    }
  }

  private loadRootIfNeeds(): Observable<readonly FileEntry<T>[]> {
    if (this.data) {
      return of(this.data);
    }
    return this.service.list().pipe(
      tap((files) => {
        this.data = files;
      })
    );
  }

  connect(): Observable<readonly FileEntry<T>[]> {
    const refresh$ = merge(
      this.expansionModel.changed,
      this.loadingModel.changed,
      this.selectionModel
        ? this.selectionModel.changed
        : (EMPTY as Observable<SelectionChange<K>>)
    );
    return merge(this.loadRootIfNeeds(), refresh$).pipe(
      map(() => this.data || [])
    );
  }

  select(file: FileEntry<T>): void {
    if (!this.selectionModel) {
      return;
    }
    this.selectionModel.select(this.trackBy(file));
  }

  deselect(file: FileEntry<T>): void {
    if (!this.selectionModel) {
      return;
    }
    this.selectionModel.deselect(this.trackBy(file));
  }

  /**
   * Switch the selection state of the file.
   * @param file
   */
  switch(file: FileEntry<T>): void {
    if (!this.selectionModel) {
      return;
    }
    if (this.selectionModel.isSelected(this.trackBy(file))) {
      this.deselect(file);
    } else {
      this.select(file);
    }
  }

  collapse(file: FileEntry<T>): void {
    this.expansionModel.deselect(this.trackBy(file));
  }

  expand(file: FileEntry<T>): void {
    if (
      !this.isExpandable(file) ||
      this.loadingModel.isSelected(this.trackBy(file))
    ) {
      return;
    }
    this.loadingModel.select(this.trackBy(file));
    this.service.list(file).subscribe({
      next: (files) => {
        file.children = files;
        this.expansionModel.select(this.trackBy(file));
        this.loadingModel.deselect(this.trackBy(file));
      },
      error: (error) => {
        console.error(error);
        this.loadingModel.deselect(this.trackBy(file));
      },
      complete: () => {
        this.loadingModel.deselect(this.trackBy(file));
      },
    });
  }

  /**
   * Toggle the expansion state of the file.
   * @param file
   */
  toggle(file: FileEntry<T>): void {
    if (this.expansionModel.isSelected(this.trackBy(file))) {
      this.collapse(file);
    } else {
      this.expand(file);
    }
  }
}
