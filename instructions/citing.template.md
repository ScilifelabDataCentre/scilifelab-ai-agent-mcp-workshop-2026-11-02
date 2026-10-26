<!--
Template for user-facing instructions regarding how to cite your service.

See the root README section "Repository contents" for a link to the related development guidelines.

These instructions can be copy-pasted, adjusted to each project's needs, and placed on the project's / service's website (if there is one).

Replace **every** {{...}} placeholder with your own value, including the ones in the citation examples.
-->

# How to cite {{SERVICE NAME}}

In line with the principles of FAIR and Open Science, we encourage the reuse and recognition of material made available on {{SERVICE NAME}}. On this page, you will find information about how to cite {{SERVICE NAME}} when reusing and referencing the content ({{CONTENT LICENSE}}), as well as the underlying code ({{CODE LICENSE}}). Please note that the information on {{SERVICE NAME}} is updated continuously, therefore it is important to refer to specific versions (or to provide access dates) within citations.

When citing {{SERVICE NAME}} or the underlying code, the format will depend on the style required by your target journal or publisher.

The instructions in the sections below cover:

- [Metadata for {{SERVICE NAME}}](#metadata-for-{{service-name}}) to include in the citations
- Full examples of how to cite...
  - ...the [website content](#citing-website-content)
  - ...the [underlying code](#citing-underlying-code)

## Metadata for {{SERVICE NAME}}

| Element                                                         | Service                                                | Code                                               |
| --------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------- |
| Name                                                            | {{SERVICE NAME}}                                       | {{SOFTWARE NAME, E.G. REPOSITORY NAME}}            |
| Contributors and organisation                                   | SciLifeLab Data Centre [^1]                            | SciLifeLab Data Centre                             |
| Version                                                         | {{INSTRUCTIONS ON WHERE TO FIND SERVICE VERSION}} [^1] | {{INSTRUCTIONS ON WHERE TO FIND SOFTWARE VERSION}} |
| Globally unique, machine-actionable persistent identifier (PID) | **RRID:** [^2] {{SERVICE RRID}}                        | **Zenodo DOI:** {{SOFTWARE DOI}}                   |

[^1]: If you are aiming to cite specific pages of {{SERVICE NAME}} (e.g. {{EXAMPLE}}), you may find that an author is mentioned and a date is given. In this case, you should also include this information in the citation. You must still include the RRID. If information is given on how to cite something featured on a given page, then that citation should be used instead of following this guide.

[^2]: The Resource Identification Portal was created in support of the Resource Identification Initiative. It aims to promote the identification, discovery, and reuse of research resources. Research Resource Identifiers (RRIDs) are persistent and unique identifiers for referencing a research resource. By citing {{SERVICE NAME}} using the RRID, you will facilitate further reuse of {{SERVICE NAME}}, enable us to track that activity, and allow others to easily find the Summary Report for usage of {{SERVICE NAME}}.

## Citing website content

The following example shows how to cite the {{SERVICE NAME}} website content using the SciCrunch format:

```text
{{SERVICE NAME}} ({{ACCESS DATE}}), SciLifeLab Data Centre, version {{SERVICE VERSION}} from {{SERVICE URL}}, RRID:{{SERVICE RRID}}.
```

## Citing underlying code

{{SERVICE NAME}} is operated by the SciLifeLab Data Centre. All of the source code used on the website is available on GitHub. The code used to produce the website is available in our [GitHub repository]({{LINK TO REPO}}).

The following example shows how to cite the underlying code of {{SERVICE NAME}}, using the APA format:

```text
SciLifeLab Data Centre ({{YEAR}}). {{SOFTWARE NAME}} (Version {{SOFTWARE VERSION}}) [Software]. Zenodo. https://doi.org/{{SOFTWARE DOI}}
```

## Journalists

Journalists are welcome to reuse images, content, or other material from {{SERVICE NAME}} for articles, blogs, social media etc. ({{CONTENT LICENSE}}). Please refer to {{SERVICE NAME}} as {{SERVICE NAME}} and link to our webpage {{SERVICE URL}} when you use the website content. You may also include our RRID [^2].
