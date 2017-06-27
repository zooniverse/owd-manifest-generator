# owd-manifest-generator
Generates Ouroboros manifests for Operation War Diary

This assumes you have diary metadata in `diaries.tsv` and additional diary
metadata in `extra.tsv`, along with images on the local filesystem.

The following command will resize those images, upload them to S3, and produce a
JSON Ouroboros manifest on S3:

```
docker run -it --rm -e DATA_PREFIX=wo/95 -v $PWD/:/data/ -v $PWD/extra.tsv:/extra.tsv -v $PWD/diaries.tsv:/diaries.tsv zooniverse/owd-manifest-generator
```

For reference, `diaries.tsv` looks something like this (with no header row):

```
1557    2       C7352254        13 Infantry Brigade  15 Battalion Royal Warwickshire Regiment
1557    3       C7352255        13 Infantry Brigade  16 Battalion Royal Warwickshire Regiment
1563    1       C14017161       14 Infantry Brigade: 1 Battalion East Surrey Regiment   14 Infantry Brigade: 1 Battalion East Surrey Regiment
```

And `extra.tsv` looks like this (note that the BOM, if present, won't cause a
problem as the file is opened with the correct encoding for this):

```
<U+FEFF>IAID    SourceLevelId   CatalogueId     ParentIAID      Reference       Title   CoveringDates   Note    CoveringFromDate        CoveringToDate  Description
C138492 5       57939   C78426  Subsubseries 34 of Subseries 1 of WO 95 <unittitle type = "Title">1 CAVALRY DIVISION</unittitle>                                        
C4554247        6       5635430 C138492 WO 95/1096              1914 Aug - Dec          19140801        19141231        <scopecontent><p>Headquarters Branches and Services: General Staff. (Described at item level)</p></scopecontent>
C14016474       7       -8269793        C4554247        WO 95/1096/1            1914 Aug 1 - 1914 Aug 31                19140801        19140831        <scopecontent>^M        <p>Headquarters Branches and Services: General Staff. </p>^M </scopecontent>
C14016475       7       -8269794        C4554247        WO 95/1096/2            1914 Sept 1 - 1914 Sept 30              19140901        19140930        <scopecontent>^M        <p>Headquarters Branches and Services: General Staff. </p>^M </scopecontent>
C14016476       7       -8269795        C4554247        WO 95/1096/3            1914 Oct 1 - 1914 Oct 31                19141001        19141031        <scopecontent>^M        <p>Headquarters Branches and Services: General Staff. </p>^M </scopecontent>
```
